use std::io::Write;
use freewili_finder_rs::{DeviceType, FreeWiliDevice, FreeWiliError, UsbDeviceType};
use serial2::SerialPort;
use thiserror::Error;
#[derive(Error, Debug)]
pub enum Error {
    #[error("Critical Error: {0}")]
    Critical(String),
    #[error("UF2 Error: {0}")]
    UF2(String),
    #[error("Flash Error: {0}")]
    Flash(String),
}
impl From<FreeWiliError> for Error {
    fn from(err: FreeWiliError) -> Self {
        Error::Critical(format!("{}", err))
    }
}
pub type Result<T, E = Error> = std::result::Result<T, E>;
#[derive(Debug)]
pub enum Uf2File {
    FreeWili(Vec<u8>, Vec<u8>),
    Standalone(Vec<u8>),
}
fn decompress_uf2(data: Vec<u8>) -> Vec<u8> {
    lz4::block::decompress(&data, None).expect("Failed to decompress UF2 data")
}
fn get_uf2_for_device_type(device_type: &DeviceType) -> Option<Uf2File> {
    match device_type {
        DeviceType::Freewili => {
            Some(
                Uf2File::FreeWili(
                    decompress_uf2(
                        include_bytes!("../assets/firmware/FreeWiliMain.uf2.lz4")
                            .to_vec(),
                    ),
                    decompress_uf2(
                        include_bytes!("../assets/firmware/FreeWiliDisplay.uf2.lz4")
                            .to_vec(),
                    ),
                ),
            )
        }
        DeviceType::Defcon2024Badge => {
            Some(
                Uf2File::Standalone(
                    decompress_uf2(
                        include_bytes!(
                            "../assets/firmware/FreeWiliDefcon2024Badge.uf2.lz4",
                        )
                            .to_vec(),
                    ),
                ),
            )
        }
        DeviceType::Defcon2025FwBadge => {
            Some(
                Uf2File::Standalone(
                    decompress_uf2(
                        include_bytes!(
                            "../assets/firmware/FreeWiliDefcon2025Badge.uf2.lz4",
                        )
                            .to_vec(),
                    ),
                ),
            )
        }
        DeviceType::Unknown | DeviceType::Uf2 | DeviceType::Winky => None,
    }
}
#[derive(Debug)]
pub enum UpdateMessage {
    Progress(i16),
    ProgressDetail(String),
    Error(String),
    Complete(std::time::Duration),
}
pub struct FreeWiliUpdater {
    unique_id: u64,
    original_device_type: DeviceType,
    message_channel: Option<std::sync::mpsc::Sender<UpdateMessage>>,
}
impl FreeWiliUpdater {
    pub fn new(
        device: &FreeWiliDevice,
        device_type_hint: Option<DeviceType>,
        message_channel: Option<std::sync::mpsc::Sender<UpdateMessage>>,
    ) -> Self {
        let unique_id = device.unique_id().unwrap_or(0);
        let original_device_type = if let Some(device_type_hint) = device_type_hint {
            device_type_hint
        } else {
            device.device_type().unwrap_or(DeviceType::Unknown)
        };
        Self {
            unique_id,
            original_device_type,
            message_channel,
        }
    }
    fn update_message(&self, message: UpdateMessage) {
        if let Some(sender) = &self.message_channel {
            println!("Sending message: {:?}", &message);
            let _ = sender.send(message);
        }
    }
    fn find_device(&self) -> Result<FreeWiliDevice> {
        for _ in 0..600 {
            match FreeWiliDevice::find_all() {
                Ok(devices) => {
                    for fw_device in devices {
                        if fw_device.unique_id()? == self.unique_id {
                            return Ok(fw_device);
                        }
                    }
                }
                Err(_) => {
                    std::thread::sleep(std::time::Duration::from_millis(10));
                    continue;
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
        Err(Error::Critical("Failed to find FreeWiliDevice".into()))
    }
    fn enter_uf2(&self) -> Result<std::time::Duration> {
        let _enter_uf2 = |port: &Option<String>| -> Result<()> {
            if let Some(port) = port {
                match SerialPort::open(port, 1200) {
                    Ok(serial_port) => {
                        self.update_message(
                            UpdateMessage::ProgressDetail(
                                format!("Port opened: {}", port),
                            ),
                        );
                        drop(serial_port);
                    }
                    Err(error) => {
                        match error.kind() {
                            std::io::ErrorKind::BrokenPipe => {}
                            _ => {
                                if let Some(31) = error.raw_os_error() {
                                    println!(
                                        "Device may be transitioning to UF2 mode (Windows error 31)",
                                    );
                                } else if error.raw_os_error().is_some() {
                                    #[cfg(not(target_os = "windows"))]
                                    {
                                        return Err(
                                            Error::Critical(
                                                format!("Failed to open port {}: {:?}", port, error),
                                            ),
                                        );
                                    }
                                } else {
                                    return Err(
                                        Error::Critical(
                                            format!(
                                                "Failed to open port to force UF2 mode {}: {:?}",
                                                port,
                                                error,
                                            ),
                                        ),
                                    );
                                }
                            }
                        }
                    }
                }
            }
            Ok(())
        };
        self.update_message(UpdateMessage::Progress(-1));
        let duration = std::time::Instant::now();
        let device = self.find_device()?;
        match device.device_type()? {
            DeviceType::Freewili => {
                let main = device.get_main_usb_device()?;
                let display = device.get_display_usb_device()?;
                if device.get_main_usb_device()?.kind == UsbDeviceType::SerialMain {
                    _enter_uf2(&main.port)?;
                }
                if device.get_display_usb_device()?.kind == UsbDeviceType::SerialDisplay
                {
                    _enter_uf2(&display.port)?;
                }
                let loop_timeout = std::time::Instant::now();
                self.update_message(
                    UpdateMessage::ProgressDetail(
                        "Waiting for device to enter UF2 mode...".into(),
                    ),
                );
                loop {
                    if loop_timeout.elapsed().as_secs() > 30 {
                        return Err(
                            Error::Critical(
                                "Timeout waiting for device to enter UF2 mode".into(),
                            ),
                        );
                    }
                    let device = self.find_device()?;
                    let main = match device.get_main_usb_device() {
                        Ok(dev) => dev,
                        Err(_) => continue,
                    };
                    let display = match device.get_display_usb_device() {
                        Ok(dev) => dev,
                        Err(_) => continue,
                    };
                    if main.kind == UsbDeviceType::MassStorage
                        && display.kind == UsbDeviceType::MassStorage
                    {
                        self.update_message(
                            UpdateMessage::ProgressDetail(
                                "Device entered UF2 mode".into(),
                            ),
                        );
                        if main.path.is_none() || display.path.is_none() {
                            std::thread::sleep(std::time::Duration::from_millis(100));
                            self.update_message(
                                UpdateMessage::ProgressDetail(
                                    "Device entered UF2 mode but paths are missing. Is it mounted?"
                                        .into(),
                                ),
                            );
                        }
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }
            DeviceType::Defcon2024Badge
            | DeviceType::Defcon2025FwBadge
            | DeviceType::Winky => {
                let main = device.get_main_usb_device()?;
                if device.get_main_usb_device()?.kind == UsbDeviceType::SerialMain {
                    _enter_uf2(&main.port)?;
                }
                let loop_timeout = std::time::Instant::now();
                self.update_message(
                    UpdateMessage::ProgressDetail(
                        "Waiting for device to enter UF2 mode...".into(),
                    ),
                );
                loop {
                    if loop_timeout.elapsed().as_secs() > 30 {
                        return Err(
                            Error::Critical(
                                "Timeout waiting for device to enter UF2 mode".into(),
                            ),
                        );
                    }
                    let device = self.find_device()?;
                    let main = match device.get_main_usb_device() {
                        Ok(dev) => dev,
                        Err(_) => continue,
                    };
                    if main.kind == UsbDeviceType::MassStorage {
                        self.update_message(
                            UpdateMessage::ProgressDetail(
                                "Device entered UF2 mode".into(),
                            ),
                        );
                        if main.path.is_none() {
                            self.update_message(
                                UpdateMessage::ProgressDetail(
                                    "Device entered UF2 mode but paths are missing. Is it mounted?"
                                        .into(),
                                ),
                            );
                            std::thread::sleep(std::time::Duration::from_millis(500));
                            continue;
                        }
                        break;
                    }
                    std::thread::sleep(std::time::Duration::from_millis(100));
                }
            }
            DeviceType::Uf2 => {}
            _ => return Err(Error::Critical("Device does not support UF2 mode".into())),
        }
        self.update_message(
            UpdateMessage::ProgressDetail(
                "Device entered UF2 mode, waiting for device to settle...".into(),
            ),
        );
        std::thread::sleep(std::time::Duration::from_millis(6000));
        Ok(duration.elapsed())
    }
    fn flash_uf2(&self) -> Result<std::time::Duration> {
        let _flash_uf2 = |name: String, path: String, data: Vec<u8>| -> Result<()> {
            let complete_path = std::path::PathBuf::from(&path).join("firmware.uf2");
            let mut f = std::fs::File::create(complete_path)
                .map_err(|e| Error::Flash(format!("Failed to create UF2 file: {}", e)))?;
            #[cfg(target_os = "macos")]
            let chunk_size: usize = 4096 * 16;
            #[cfg(not(target_os = "macos"))]
            let chunk_size: usize = 4096 * 32;
            for (i, d) in data.chunks(chunk_size).enumerate() {
                let progress = ((i as f32
                            / ((data.len() + chunk_size - 1).div_ceil(chunk_size))
                                as f32) * 100.0) as i16;
                self.update_message(
                    UpdateMessage::ProgressDetail(
                        format!(
                            "{name} Flashing chunk {i} of {} ({progress}%) ({path})",
                            (data.len() + chunk_size - 1).div_ceil(chunk_size),
                        ),
                    ),
                );
                self.update_message(
                    UpdateMessage::Progress(progress),
                );
                f.write_all(d)
                    .map_err(|e| Error::Flash(
                        format!("Failed to write UF2 file chunk: {}", e),
                    ))?;
                f.sync_all()
                    .map_err(|e| Error::Flash(
                        format!("Failed to sync UF2 file: {}", e),
                    ))?;
            }
            self.update_message(UpdateMessage::Progress(100));
            drop(f);
            Ok(())
        };
        let duration = std::time::Instant::now();
        let device = self.find_device()?;
        let device_type = &self.original_device_type;
        match get_uf2_for_device_type(device_type) {
            Some(Uf2File::FreeWili(main_uf2, display_uf2)) => {
                self.update_message(UpdateMessage::ProgressDetail(
                    "Flashing FreeWili UF2 files...".into(),
                ));
                if let Some(path) = device.get_display_usb_device()?.path {
                    _flash_uf2("Display".to_string(), path, display_uf2.clone())?;
                } else {
                    return Err(Error::Flash("Display device path not found".into()));
                }
                if let Some(path) = device.get_main_usb_device()?.path {
                    _flash_uf2("Main".to_string(), path, main_uf2.clone())?;
                } else {
                    return Err(Error::Flash("Main device path not found".into()));
                }
            }
            Some(Uf2File::Standalone(main_uf2)) => {
                if let Some(path) = device.get_main_usb_device()?.path {
                    _flash_uf2("Main".to_string(), path, main_uf2.clone())?;
                } else {
                    return Err(Error::Flash("Main device path not found".into()));
                }
            }
            None => {
                self.update_message(UpdateMessage::Progress(100));
                return Err(
                    Error::UF2(
                        format!(
                            "No firmware data available for device type: {:?}",
                            device_type,
                        ),
                    ),
                );
            }
        };
        Ok(duration.elapsed())
    }
    pub fn update(&self) -> Result<std::time::Duration> {
        self.update_message(
            UpdateMessage::ProgressDetail("Entering UF2 mode...".into()),
        );
        let uf2_duration = self.enter_uf2()?;
        self.update_message(UpdateMessage::ProgressDetail("Flashing UF2...".into()));
        let flash_duration = self.flash_uf2()?;
        self.update_message(UpdateMessage::Complete(uf2_duration + flash_duration));
        Ok(uf2_duration + flash_duration)
    }
}

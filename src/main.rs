#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]
mod flasher;
use dioxus::{
    desktop::{
        Config, WindowBuilder,
        tao::{dpi::LogicalSize, window::{Icon, WindowSizeConstraints}},
        wry::dpi::{LogicalUnit, PixelUnit},
    },
    prelude::*,
};
use freewili_finder_rs::{DeviceType, FreeWiliDevice, device_type_name};
mod built_info {
    include!(concat!(env!("OUT_DIR"), "/built.rs"));
}
use crate::flasher::FreeWiliUpdater;
#[cfg(not(debug_assertions))]
static MAIN_CSS: Option<Asset> = None;
#[cfg(not(debug_assertions))]
const MAIN_CSS_CONTENT: &str = include_str!("../assets/main.css");
#[cfg(debug_assertions)]
static MAIN_CSS: Option<Asset> = Some(asset!("assets/main.css"));
#[cfg(debug_assertions)]
const MAIN_CSS_CONTENT: &str = "";
const HEADER_PNG_BYTES: &[u8] = include_bytes!("../assets/header.png");
const DEFCON32_PNG_BYTES: &[u8] = include_bytes!("../assets/defcon32.png");
const DEFCON33_PNG_BYTES: &[u8] = include_bytes!("../assets/defcon33.png");
const FREEWILI_PNG_BYTES: &[u8] = include_bytes!("../assets/freewili.png");
const UNKNOWN_PNG_BYTES: &[u8] = include_bytes!("../assets/unknown.png");
const ICON_BYTES: &[u8] = include_bytes!("../icons/icon.png");
const ICON_ICO_BYTES: &[u8] = include_bytes!("../icons/icon.ico");
fn bytes_to_data_url(bytes: &[u8], mime_type: &str) -> String {
    use base64::Engine;
    let encoded = base64::engine::general_purpose::STANDARD.encode(bytes);
    format!("data:{};base64,{}", mime_type, encoded)
}
fn get_device_image_data_url(device_type: &DeviceType) -> String {
    let bytes = match device_type {
        DeviceType::Defcon2024Badge => DEFCON32_PNG_BYTES,
        DeviceType::Defcon2025FwBadge => DEFCON33_PNG_BYTES,
        DeviceType::Freewili => FREEWILI_PNG_BYTES,
        DeviceType::Uf2 | DeviceType::Winky | DeviceType::Unknown => UNKNOWN_PNG_BYTES,
    };
    bytes_to_data_url(bytes, "image/png")
}
fn main() {
    let window_title = format!(
        "Free-WILi Updater v{} ({})",
        built_info::PKG_VERSION,
        built_info::GIT_COMMIT_HASH_SHORT.unwrap_or("N/A"),
    );
    let window_builder = WindowBuilder::new()
        .with_title(window_title)
        .with_window_icon({
            if let Ok(img) = image::load_from_memory(ICON_ICO_BYTES) {
                let rgba = img.to_rgba8();
                let (width, height) = rgba.dimensions();
                Icon::from_rgba(rgba.into_raw(), width, height).ok()
            } else if let Ok(img) = image::load_from_memory(ICON_BYTES) {
                let rgba = img.to_rgba8();
                let (width, height) = rgba.dimensions();
                Icon::from_rgba(rgba.into_raw(), width, height).ok()
            } else {
                if let Ok(img) = image::open("icons/icon.ico") {
                    let rgba = img.to_rgba8();
                    let (width, height) = rgba.dimensions();
                    Icon::from_rgba(rgba.into_raw(), width, height).ok()
                } else {
                    None
                }
            }
        })
        .with_inner_size(LogicalSize::new(400.0, 600.0))
        .with_inner_size_constraints(WindowSizeConstraints {
            min_width: Some(PixelUnit::Logical(LogicalUnit(250.0))),
            min_height: Some(PixelUnit::Logical(LogicalUnit(400.0))),
            max_width: None,
            max_height: None,
        })
        .with_resizable(true);
    let config = Config::new().with_window(window_builder).with_menu(None);
    dioxus::LaunchBuilder::desktop().with_cfg(config).launch(App);
}
#[component]
fn App() -> Element {
    let device_list = use_signal(Vec::<FreeWiliDevice>::new);
    let selected_device_index = use_signal(|| None::<u64>);
    let selected_device = use_signal(|| None::<FreeWiliDevice>);
    let is_flashing = use_signal(|| false);
    let is_refreshing = use_signal(|| false);
    let flash_status = use_signal(String::new);
    let flash_progress = use_signal(|| 0i16);
    let device_type_hint = use_signal(|| None::<DeviceType>);
    use_context_provider(|| device_list);
    use_context_provider(|| selected_device_index);
    use_context_provider(|| selected_device);
    use_context_provider(|| is_flashing);
    use_context_provider(|| is_refreshing);
    use_context_provider(|| flash_status);
    use_context_provider(|| flash_progress);
    use_context_provider(|| device_type_hint);
    spawn(async move {
        refresh_devices(
                None,
                is_refreshing,
                device_list,
                selected_device_index,
                selected_device,
            )
            .await;
    });
    rsx! {
        if cfg!(debug_assertions) {
            document::Stylesheet { href: MAIN_CSS.unwrap() }
        } else {
            document::Style { {MAIN_CSS_CONTENT} }
        }
        FreeWiliUpdaterApp {}
    }
}
#[component]
fn HeaderComponent() -> Element {
    let header_image_url = bytes_to_data_url(HEADER_PNG_BYTES, "image/png");
    rsx! {
        div { class: "header",
            img { src: "{header_image_url}", class: "header-logo" }
        }
    }
}
#[component]
fn DeviceSelectionComponent() -> Element {
    let device_list = use_context::<Signal<Vec<FreeWiliDevice>>>();
    let mut selected_device_index = use_context::<Signal<Option<u64>>>();
    let mut selected_device = use_context::<Signal<Option<FreeWiliDevice>>>();
    let is_refreshing = use_context::<Signal<bool>>();
    let is_flashing = use_context::<Signal<bool>>();
    let _refresh_devices = move |_| {
        spawn(async move {
            refresh_devices(
                    None,
                    is_refreshing,
                    device_list,
                    selected_device_index,
                    selected_device,
                )
                .await;
        });
    };
    rsx! {
        select {
            class: "dropdown",
            onchange: move |evt| {
                if let Ok(index) = evt.value().parse::<u64>() {
                    println!("Selected device index: {}", index);
                    selected_device_index.set(Some(index));
                    selected_device.set(None);
                    for device in device_list.read().iter() {
                        if let Ok(unique_id) = device.unique_id() && index == unique_id {
                            println!("Setting selected device to: {}", device);
                            selected_device.set(Some(device.clone()));
                            break;
                        }
                    }
                }
            },
            disabled: is_flashing() || is_refreshing(),
            if device_list.read().is_empty() {
                option { value: "", "No devices found" }
            } else {
                for (i , device) in device_list.read().iter().enumerate() {
                    option {
                        value: "{device.unique_id().unwrap_or(0)}",
                        selected: selected_device_index
                            .read()
                            .is_some_and(|idx| idx == device.unique_id().unwrap_or(0)),
                        "{i+1}) {device}"
                    }
                }
            }
        }
        button {
            class: "refresh-button",
            onclick: _refresh_devices,
            disabled: is_flashing() || is_refreshing(),
            if is_refreshing() {
                "⏳ Refreshing..."
            } else {
                "🔄 Refresh"
            }
        }
    }
}
#[component]
fn CenterMessageComponent() -> Element {
    let selected_device = use_context::<Signal<Option<FreeWiliDevice>>>();
    rsx! {
        div { class: "center-message",
            if let Some(device) = selected_device.read().as_ref() {
                p { "{device}" }
                if let Ok(main_usb) = device.get_main_usb_device() {
                    p { "{main_usb}" }
                }
                if let Ok(display_usb) = device.get_display_usb_device() {
                    p { "{display_usb}" }
                }
            } else {
                p { "Click refresh to scan for devices." }
            }
        }
    }
}
/// Async function to refresh the device list and maintain the previously selected device
///
/// This function is meant to be spawned as a background task to refresh the list of devices
/// periodically. It takes an optional initial delay before starting the refresh loop.
///
/// The function clears the device list initially to avoid freeing handles after find_all()
/// and then tries to find all devices. If the list of devices is empty, it waits for 100ms
/// and retries. This is done to avoid freeing handles for devices that are still being
/// enumerated.
///
/// After the initial refresh, the function tries to maintain the previous selection if
/// still valid. If the previously selected device is not found in the new list, the
/// function sets the selected device index to None and the selected device to the first
/// device in the list. If the previously selected device is found, the function sets the
/// selected device index to the unique ID of the device and the selected device to the
/// device itself.
///
/// The function sets the is_refreshing signal to true at the start and false at the end.
async fn refresh_devices(
    initial_delay: Option<u64>,
    mut is_refreshing: Signal<bool>,
    mut device_list: Signal<Vec<FreeWiliDevice>>,
    mut selected_device_index: Signal<Option<u64>>,
    mut selected_device: Signal<Option<FreeWiliDevice>>,
) {
    is_refreshing.set(true);
    println!("Refreshing device list...");
    if let Some(initial_delay) = initial_delay {
        tokio::time::sleep(tokio::time::Duration::from_millis(initial_delay)).await;
    } else {
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
    loop {
        device_list.clear();
        if let Ok(found_devices) = FreeWiliDevice::find_all() {
            device_list.replace(found_devices);
            break;
        }
        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    }
    if let Some(previous_selected_index) = selected_device_index() {
        selected_device_index.set(None);
        for device in device_list() {
            if let Ok(unique_id) = device.unique_id()
                && previous_selected_index == unique_id
            {
                selected_device_index.set(Some(unique_id));
                selected_device.set(Some(device.clone()));
                break;
            }
        }
    } else {
        selected_device_index.set(None);
        if let Some(device) = device_list().first() {
            selected_device.set(Some(device.clone()));
        }
    }
    is_refreshing.set(false);
}
#[component]
fn FlashComponent() -> Element {
    let mut is_flashing = use_context::<Signal<bool>>();
    let mut flash_status = use_context::<Signal<String>>();
    let mut flash_progress = use_context::<Signal<i16>>();
    let mut device_type_hint = use_context::<Signal<Option<DeviceType>>>();
    let is_refreshing = use_context::<Signal<bool>>();
    let device_list = use_context::<Signal<Vec<FreeWiliDevice>>>();
    let selected_device_index = use_context::<Signal<Option<u64>>>();
    let selected_device = use_context::<Signal<Option<FreeWiliDevice>>>();
    let start_flash = move |_| {
        if selected_device().is_none() || is_flashing() {
            return;
        }
        let device = selected_device().clone().unwrap();
        is_flashing.set(true);
        flash_status.set("Starting flash process...".to_string());
        flash_progress.set(-1);
        let (tx, rx) = std::sync::mpsc::channel::<crate::flasher::UpdateMessage>();
        let tx_for_updater = tx.clone();
        let updater = FreeWiliUpdater::new(
            &device,
            device_type_hint(),
            Some(tx_for_updater),
        );
        spawn(async move {
            use crate::flasher::UpdateMessage;
            loop {
                tokio::time::sleep(tokio::time::Duration::from_millis(10)).await;
                match rx.try_recv() {
                    Ok(msg) => {
                        match msg {
                            UpdateMessage::ProgressDetail(s) => flash_status.set(s),
                            UpdateMessage::Progress(p) => {
                                flash_progress.set(p);
                            }
                            UpdateMessage::Error(e) => {
                                flash_status.set(format!("Flash error: {}", e))
                            }
                            UpdateMessage::Complete(d) => {
                                flash_status
                                    .set(
                                        format!(
                                            "Flash completed successfully in {:.2} seconds",
                                            d.as_secs_f32(),
                                        ),
                                    )
                            }
                        }
                    }
                    Err(std::sync::mpsc::TryRecvError::Empty) => continue,
                    Err(std::sync::mpsc::TryRecvError::Disconnected) => break,
                }
            }
            is_flashing.set(false);
            let _refresh_devices = move || {
                spawn(async move {
                    refresh_devices(
                            Some(6000),
                            is_refreshing,
                            device_list,
                            selected_device_index,
                            selected_device,
                        )
                        .await;
                });
            };
            _refresh_devices();
        });
        std::thread::spawn(move || {
            match updater.update() {
                Ok(duration) => {
                    let _ = tx.send(crate::flasher::UpdateMessage::Complete(duration));
                }
                Err(e) => {
                    let _ = tx
                        .send(crate::flasher::UpdateMessage::Error(format!("{}", e)));
                    let _ = tx.send(crate::flasher::UpdateMessage::Progress(0));
                }
            }
            drop(tx);
        });
    };
    rsx! {
        div { class: "status-area",
            p { class: "status-message", "{flash_status()}" }
        }
        if flash_progress() >= 0 {
            progress {
                class: "flash-progress",
                max: 100,
                value: "{flash_progress()}",
            }
        } else {
            progress { class: "flash-progress indeterminate", max: 100, value: "0" }
        }
        if let Some(device) = selected_device().as_ref() {
            if let Ok(device_type) = device.device_type() {
                if device_type == DeviceType::Uf2 && !is_flashing() {
                    select {
                        class: "dropdown",
                        onchange: move |evt| {
                            println!("Selected device type hint: {}", evt.value());
                            match evt.value().as_str() {
                                "NA" => device_type_hint.set(None),
                                "Defcon2024Badge" => {
                                    println!("Setting device type hint to Defcon2024Badge");
                                    device_type_hint.set(Some(DeviceType::Defcon2024Badge));
                                }
                                "Defcon2025FwBadge" => {
                                    println!("Setting device type hint to Defcon2025FwBadge");
                                    device_type_hint.set(Some(DeviceType::Defcon2025FwBadge));
                                }
                                _ => {
                                    println!("Unknown device type hint: {}", evt.value());
                                    device_type_hint.set(None);
                                }
                            }
                        },
                        disabled: is_flashing(),
                        option { value: "NA", "Please Select a Device Type for UF2 device..." }
                        option { value: "Defcon2024Badge",
                            "{device_type_name(DeviceType::Defcon2024Badge).unwrap_or(\"Defcon2024Badge\".to_string())}"
                        }
                        option { value: "Defcon2025FwBadge",
                            "{device_type_name(DeviceType::Defcon2025FwBadge).unwrap_or(\"Defcon2025FwBadge\".to_string())}"
                        }
                    }
                }
            }
        }
        button {
            class: "flash-button",
            onclick: start_flash,
            disabled: is_flashing() || selected_device().is_none(),
            if is_flashing() {
                "⏳ Flashing..."
            } else {
                "⚡ Start Flash"
            }
        }
    }
}
#[component]
fn DeviceDisplayComponent() -> Element {
    let selected_device = use_context::<Signal<Option<FreeWiliDevice>>>();
    let device_type_hint = use_context::<Signal<Option<DeviceType>>>();
    rsx! {
        div {
            class: if selected_device().is_some() { "device-display" } else { "device-display no-device" },
            style: {
                if let Some(device) = selected_device().as_ref() {
                    if let Ok(device_type) = device.device_type() {
                        let hint = device_type_hint();
                        println!("Device type: {:?}, hint: {:?}", device_type, hint);
                        let image_url = match hint {
                            Some(hint_type) => get_device_image_data_url(&hint_type),
                            None => get_device_image_data_url(&device_type),
                        };
                        format!("--device-bg-image: url({});", image_url)
                    } else {
                        String::new()
                    }
                } else {
                    String::new()
                }
            },
            div { class: "device-overlay", CenterMessageComponent {} }
        }
    }
}
#[component]
pub fn FreeWiliUpdaterApp() -> Element {
    rsx! {
        div { class: "updater-container",
            HeaderComponent {}
            div { class: "top-controls", DeviceSelectionComponent {} }
            DeviceDisplayComponent {}
            div { class: "bottom-controls", FlashComponent {} }
        }
    }
}

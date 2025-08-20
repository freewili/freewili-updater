use std::fs;
use std::io::{Read, Write};
use std::path::Path;
fn main() {
    let firmware_files = [
        (
            "assets/freewili-firmware/freewili_main.uf2",
            "assets/firmware/FreeWiliMain.uf2.lz4",
        ),
        (
            "assets/freewili-firmware/freewili_display.uf2",
            "assets/firmware/FreeWiliDisplay.uf2.lz4",
        ),
        (
            "assets/freewili-firmware/defcon32_badge.uf2",
            "assets/firmware/FreeWiliDefcon2024Badge.uf2.lz4",
        ),
        (
            "assets/freewili-firmware/defcon33_badge.uf2",
            "assets/firmware/FreeWiliDefcon2025Badge.uf2.lz4",
        ),
    ];
    for (input_path, _) in &firmware_files {
        println!("cargo:rerun-if-changed={}", input_path);
    }
    println!("cargo:rerun-if-changed=assets/main.css");
    let firmware_dir = Path::new("assets/firmware");
    if !firmware_dir.exists() {
        fs::create_dir_all(firmware_dir).expect("Failed to create firmware directory");
    }
    for (input_path, output_path) in firmware_files {
        compress_file(input_path, output_path)
            .unwrap_or_else(|_| panic!("Failed to compress {}", input_path));
    }
}
fn compress_file(
    input_path: &str,
    output_path: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let input_path = Path::new(input_path);
    let output_path = Path::new(output_path);
    let mut input_file = fs::File::open(input_path)?;
    let mut input_data = Vec::new();
    input_file.read_to_end(&mut input_data)?;
    let compressed_data = lz4::block::compress(
        &input_data,
        Some(lz4::block::CompressionMode::HIGHCOMPRESSION(12)),
        true,
    )?;
    let mut output_file = fs::File::create(output_path)?;
    output_file.write_all(&compressed_data)?;
    let original_size = input_data.len();
    let compressed_size = compressed_data.len();
    let ratio = (compressed_size as f64 / original_size as f64) * 100.0;
    println!(
        "cargo:warning=Compressed {:?}: {} bytes -> {} bytes ({:.1}%)",
        input_path.file_name().unwrap(),
        original_size,
        compressed_size,
        ratio,
    );
    built::write_built_file().expect("Failed to acquire build-time information");
    Ok(())
}

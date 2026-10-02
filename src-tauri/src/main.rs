#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::error::Error;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder};

struct Backend(Mutex<Option<Child>>);

fn backend_path() -> Result<PathBuf, Box<dyn Error>> {
    let installed = std::env::current_exe()?
        .parent()
        .ok_or("desktop executable has no parent directory")?
        .join("backend")
        .join("TallybeamBackend.exe");
    if installed.exists() {
        return Ok(installed);
    }
    let development = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("dist")
        .join("TallybeamBackend")
        .join("TallybeamBackend.exe");
    if development.exists() {
        return Ok(development);
    }
    Err("Tallybeam Python backend is missing; run scripts/build-windows.ps1".into())
}

fn free_port() -> Result<u16, Box<dyn Error>> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    Ok(listener.local_addr()?.port())
}

fn backend_responds(port: u16) -> bool {
    let address = ([127, 0, 0, 1], port).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(250)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    if stream.write_all(b"GET /api/health HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n").is_err() {
        return false;
    }
    let mut response = String::new();
    stream.read_to_string(&mut response).is_ok()
        && response.contains("\"service\": \"tallybeam\"")
}

fn stop_backend(app: &tauri::AppHandle) {
    if let Some(mut child) = app.state::<Backend>().0.lock().unwrap().take() {
        let _ = child.kill();
        let _ = child.wait();
    }
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _, _| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let port = free_port()?;
            let mut command = Command::new(backend_path()?);
            command
                .arg("--no-browser")
                .arg("--port")
                .arg(port.to_string())
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null());
            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(0x0800_0000); // CREATE_NO_WINDOW
            }
            let child = command.spawn()?;
            *app.state::<Backend>().0.lock().unwrap() = Some(child);

            let deadline = Instant::now() + Duration::from_secs(20);
            while Instant::now() < deadline {
                if backend_responds(port) {
                    break;
                }
                let exited = {
                    let state = app.state::<Backend>();
                    let mut backend = state.0.lock().unwrap();
                    if let Some(child) = backend.as_mut() {
                        child.try_wait()?.is_some()
                    } else {
                        true
                    }
                };
                if exited {
                    stop_backend(app.handle());
                    return Err("Python backend exited during startup".into());
                }
                std::thread::sleep(Duration::from_millis(200));
            }
            if !backend_responds(port) {
                stop_backend(app.handle());
                return Err("Python backend did not become ready".into());
            }

            let url = format!("http://127.0.0.1:{port}/").parse()?;
            WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title("Tallybeam")
                .decorations(false)
                .background_color(tauri::window::Color(48, 48, 51, 255))
                .on_navigation(move |destination| {
                    destination.scheme() == "http"
                        && destination.host_str() == Some("127.0.0.1")
                        && destination.port_or_known_default() == Some(port)
                })
                .inner_size(1280.0, 900.0)
                .min_inner_size(800.0, 560.0)
                .build()?;
            Ok(())
        })
        .on_window_event(|window, event| {
            if window.label() == "main" && matches!(event, tauri::WindowEvent::Destroyed) {
                window.app_handle().exit(0);
            }
        })
        .build(tauri::generate_context!())
        .expect("failed to initialize Tallybeam")
        .run(|app, event| {
            if let tauri::RunEvent::Exit = event {
                stop_backend(app);
            }
        });
}

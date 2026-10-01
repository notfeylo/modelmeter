//! File discovery only. This process never reads session contents.
use std::{
    env, fs,
    path::{Path, PathBuf},
};

fn files(root: &Path, suffix: &str) -> Vec<PathBuf> {
    let mut pending = vec![root.to_path_buf()];
    let mut found = Vec::new();
    while let Some(dir) = pending.pop() {
        let Ok(entries) = fs::read_dir(dir) else {
            continue;
        };
        for entry in entries.flatten() {
            let Ok(kind) = entry.file_type() else {
                continue;
            };
            let path = entry.path();
            if kind.is_dir() {
                // Avoid following directory links outside a user's session folder.
                pending.push(path);
            } else if kind.is_file() && path.to_string_lossy().ends_with(suffix) {
                found.push(path);
            }
        }
    }
    found.sort();
    found
}

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() != 3 || !matches!(args[2].as_str(), ".json" | ".jsonl") {
        eprintln!("usage: tallybeam-indexer <root> <.json|.jsonl>");
        std::process::exit(2);
    }
    for path in files(Path::new(&args[1]), &args[2]) {
        println!("{}", path.display());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn empty_directory_is_empty() {
        let temp = env::temp_dir().join(format!("tallybeam-indexer-{}", std::process::id()));
        fs::create_dir_all(&temp).unwrap();
        assert!(files(&temp, ".jsonl").is_empty());
        fs::remove_dir(&temp).unwrap();
    }
}

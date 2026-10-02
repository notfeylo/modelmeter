import { isTauri } from "@tauri-apps/api/core";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { Maximize2, Minus, X } from "lucide-react";

export function DesktopTitlebar() {
  if (!isTauri()) return null;

  const appWindow = getCurrentWindow();

  return (
    <header className="desktop-titlebar sticky top-0 z-50 flex h-10 items-center bg-background/55 text-foreground backdrop-blur-xl select-none">
      <div data-tauri-drag-region="deep" className="flex h-full min-w-0 flex-1 items-center gap-2 px-4">
        <img src="/logo.svg" alt="" className="size-4" draggable={false} />
        <span className="text-xs font-semibold tracking-wide">Modelmeter</span>
      </div>
      <div className="flex h-full items-center" aria-label="Window controls">
        <button type="button" className="desktop-window-button" aria-label="Minimize window" title="Minimize" onClick={() => void appWindow.minimize()}>
          <Minus size={15} strokeWidth={1.7} />
        </button>
        <button type="button" className="desktop-window-button" aria-label="Maximize or restore window" title="Maximize or restore" onClick={() => void appWindow.toggleMaximize()}>
          <Maximize2 size={13} strokeWidth={1.6} />
        </button>
        <button type="button" className="desktop-window-button desktop-window-close" aria-label="Close window" title="Close" onClick={() => void appWindow.close()}>
          <X size={16} strokeWidth={1.7} />
        </button>
      </div>
    </header>
  );
}

import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import "./index.css"
import App from "./App.tsx"
import { ThemeProvider } from "@/components/theme-provider.tsx"
import { LocaleProvider } from "@/lib/i18n/index.tsx"
import { DesktopTitlebar } from "@/components/desktop-titlebar.tsx"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="tallybeam-theme-v2">
      <LocaleProvider>
        <DesktopTitlebar />
        <App />
      </LocaleProvider>
    </ThemeProvider>
  </StrictMode>,
)

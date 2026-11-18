import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import App from "./App"
import { ThemeProvider } from "./context/ThemeContext"
import { AuthProvider } from "./context/AuthContext"
import "./index.css"

function showStartupError(source: string, error: unknown) {
  const rootElement = document.getElementById("root")
  if (!rootElement || rootElement.dataset.startupErrorShown === "true") return

  rootElement.dataset.startupErrorShown = "true"
  const message = error instanceof Error ? error.message : String(error)
  const details = error instanceof Error ? error.stack ?? message : message
  const panel = document.createElement("main")
  panel.style.cssText = "max-width:760px;margin:48px auto;padding:24px;font:16px/1.5 system-ui,sans-serif;color:#f8fafc;background:#172033;border-radius:12px"
  const heading = document.createElement("h1")
  heading.textContent = "TutorInn couldn't start"
  const explanation = document.createElement("p")
  explanation.textContent = "A browser-side error stopped the page from rendering. Please share the diagnostic details below with the TutorInn developer."
  const sourceLabel = document.createElement("p")
  sourceLabel.textContent = `Error source: ${source}`
  const messageLabel = document.createElement("p")
  messageLabel.textContent = `Message: ${message}`
  const pre = document.createElement("pre")
  pre.style.cssText = "white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;background:#0b1220;border-radius:8px;font-size:12px"
  pre.textContent = details
  panel.append(heading, explanation, sourceLabel, messageLabel, pre)
  rootElement.replaceChildren(panel)
  console.error("[TutorInn startup diagnostic]", source, error)
}

window.addEventListener("error", (event) => {
  showStartupError("window.error", event.error ?? event.message)
})

window.addEventListener("unhandledrejection", (event) => {
  showStartupError("unhandledrejection", event.reason)
})

const rootElement = document.getElementById("root")
if (!rootElement) {
  showStartupError("application bootstrap", new Error('Missing element with id="root"'))
} else {
  const root = createRoot(rootElement, {
    onUncaughtError(error, info) {
      showStartupError("React onUncaughtError", error instanceof Error ? error : new Error(String(error) + "\\n" + info.componentStack))
    },
    onCaughtError(error) {
      console.error("[TutorInn caught React error]", error)
    },
    onRecoverableError(error) {
      console.warn("[TutorInn recoverable React error]", error)
    },
  })

  root.render(
    <StrictMode>
      <ThemeProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
    </StrictMode>,
  )
}

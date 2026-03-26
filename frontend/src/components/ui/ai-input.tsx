import React from "react"
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import { cx as _cx } from "class-variance-authority"
import { AnimatePresence, motion } from "motion/react"
import { Send, X } from "lucide-react"
import { marked } from "marked"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import AnthropicDark from "@/components/kokonutui/anthropic-dark"

interface OrbProps {
  dimension?: string
  className?: string
  tones?: {
    base?: string
    accent1?: string
    accent2?: string
    accent3?: string
  }
  spinDuration?: number
}

const orbStyleId = "color-orb-styles"

function ensureOrbStyles() {
  if (typeof document === "undefined") return
  if (document.getElementById(orbStyleId)) return
  const style = document.createElement("style")
  style.id = orbStyleId
  style.textContent = `
    @property --angle {
      syntax: "<angle>";
      inherits: false;
      initial-value: 0deg;
    }

    .color-orb {
      display: grid;
      grid-template-areas: "stack";
      overflow: hidden;
      border-radius: 50%;
      position: relative;
      transform: scale(1.1);
    }

    .color-orb::before,
    .color-orb::after {
      content: "";
      display: block;
      grid-area: stack;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      transform: translateZ(0);
    }

    .color-orb::before {
      background:
        conic-gradient(from calc(var(--angle) * 2) at 25% 70%, var(--accent3), transparent 20% 80%, var(--accent3)),
        conic-gradient(from calc(var(--angle) * 2) at 45% 75%, var(--accent2), transparent 30% 60%, var(--accent2)),
        conic-gradient(from calc(var(--angle) * -3) at 80% 20%, var(--accent1), transparent 40% 60%, var(--accent1)),
        conic-gradient(from calc(var(--angle) * 2) at 15% 5%, var(--accent2), transparent 10% 90%, var(--accent2)),
        conic-gradient(from calc(var(--angle) * 1) at 20% 80%, var(--accent1), transparent 10% 90%, var(--accent1)),
        conic-gradient(from calc(var(--angle) * -2) at 85% 10%, var(--accent3), transparent 20% 80%, var(--accent3));
      box-shadow: inset var(--base) 0 0 var(--shadow) calc(var(--shadow) * 0.2);
      filter: blur(var(--blur)) contrast(var(--contrast));
      animation: orb-spin var(--spin-duration) linear infinite;
    }

    .color-orb::after {
      background-image: radial-gradient(circle at center, var(--base) var(--dot), transparent var(--dot));
      background-size: calc(var(--dot) * 2) calc(var(--dot) * 2);
      backdrop-filter: blur(calc(var(--blur) * 2)) contrast(calc(var(--contrast) * 2));
      mix-blend-mode: overlay;
      mask-image: radial-gradient(black var(--mask), transparent 75%);
    }

    @keyframes orb-spin {
      to { --angle: 360deg; }
    }

    @media (prefers-reduced-motion: reduce) {
      .color-orb::before { animation: none; }
    }
  `
  document.head.appendChild(style)
}

const ColorOrb: React.FC<OrbProps> = ({
  dimension = "192px",
  className,
  tones,
  spinDuration = 20,
}) => {
  React.useEffect(() => { ensureOrbStyles() }, [])

  const fallbackTones = {
    base: "oklch(95% 0.02 264.695)",
    accent1: "oklch(75% 0.15 350)",
    accent2: "oklch(80% 0.12 200)",
    accent3: "oklch(78% 0.14 280)",
  }
  const palette = { ...fallbackTones, ...tones }
  const dimValue = parseInt(dimension.replace("px", ""), 10)
  const blurStrength = dimValue < 50 ? Math.max(dimValue * 0.008, 1) : Math.max(dimValue * 0.015, 4)
  const contrastStrength = dimValue < 50 ? Math.max(dimValue * 0.004, 1.2) : Math.max(dimValue * 0.008, 1.5)
  const pixelDot = dimValue < 50 ? Math.max(dimValue * 0.004, 0.05) : Math.max(dimValue * 0.008, 0.1)
  const shadowRange = dimValue < 50 ? Math.max(dimValue * 0.004, 0.5) : Math.max(dimValue * 0.008, 2)
  const maskRadius = dimValue < 30 ? "0%" : dimValue < 50 ? "5%" : dimValue < 100 ? "15%" : "25%"
  const adjustedContrast = dimValue < 30 ? 1.1 : dimValue < 50 ? Math.max(contrastStrength * 1.2, 1.3) : contrastStrength

  return (
    <div
      className={cn("color-orb", className)}
      style={{
        width: dimension,
        height: dimension,
        "--base": palette.base,
        "--accent1": palette.accent1,
        "--accent2": palette.accent2,
        "--accent3": palette.accent3,
        "--spin-duration": `${spinDuration}s`,
        "--blur": `${blurStrength}px`,
        "--contrast": adjustedContrast,
        "--dot": `${pixelDot}px`,
        "--shadow": `${shadowRange}px`,
        "--mask": maskRadius,
      } as React.CSSProperties}
    />
  )
}

const SPEED_FACTOR = 1
const FORM_WIDTH = 400
// eslint-disable-next-line @typescript-eslint/no-unused-vars
const FORM_HEIGHT = 280

interface ContextShape {
  showForm: boolean
  successFlag: boolean
  triggerOpen: () => void
  triggerClose: () => void
}

const FormContext = React.createContext({} as ContextShape)
const useFormContext = () => React.useContext(FormContext)

interface MorphPanelProps {
  neighborhoodName?: string
  className?: string
}

export function MorphPanel({ neighborhoodName, className }: MorphPanelProps) {
  const wrapperRef = React.useRef<HTMLDivElement>(null)
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null)

  const [showForm, setShowForm] = React.useState(false)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [_successFlag, _setSuccessFlag] = React.useState(false)
  const [response, setResponse] = React.useState("")
  const [loading, setLoading] = React.useState(false)
  const responseRef = React.useRef<HTMLDivElement>(null)

  const triggerClose = React.useCallback(() => {
    setShowForm(false)
    setResponse("")
    textareaRef.current?.blur()
  }, [])

  const triggerOpen = React.useCallback(() => {
    setShowForm(true)
    setTimeout(() => { textareaRef.current?.focus() })
  }, [])

  const handleSuccess = React.useCallback(async (message: string) => {
    if (!message.trim()) return
    setLoading(true)
    setResponse("")

    try {
      const resp = await fetch("/api/ai-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim(), neighborhood: neighborhoodName || null }),
      })

      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}))
        setResponse(errBody.detail || errBody.error || "AI service is temporarily unavailable. Please try again.")
        setLoading(false)
        return
      }

      const reader = resp.body?.getReader()
      const decoder = new TextDecoder()
      let accumulated = ""

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          const chunk = decoder.decode(value, { stream: true })
          for (const line of chunk.split("\n")) {
            if (line.startsWith("data: ")) {
              const data = line.slice(6)
              if (data === "[DONE]") continue
              try {
                const parsed = JSON.parse(data)
                if (parsed.text) {
                  accumulated += parsed.text
                  setResponse(accumulated)
                  if (responseRef.current) responseRef.current.scrollTop = responseRef.current.scrollHeight
                }
                if (parsed.error) setResponse(accumulated ? accumulated + "\n\n⚠ " + parsed.error : parsed.error)
              } catch { /* skip */ }
            }
          }
        }
      }
    } catch {
      setResponse("Could not reach the AI service. Please try again in a moment.")
    } finally {
      setLoading(false)
    }
  }, [neighborhoodName])

  React.useEffect(() => {
    function clickOutsideHandler(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node) && showForm) {
        triggerClose()
      }
    }
    document.addEventListener("mousedown", clickOutsideHandler)
    return () => document.removeEventListener("mousedown", clickOutsideHandler)
  }, [showForm, triggerClose])

  const ctx = React.useMemo(
    () => ({ showForm, successFlag: _successFlag, triggerOpen, triggerClose }),
    [showForm, _successFlag, triggerOpen, triggerClose]
  )

  return (
    <div className={cn("relative", className)} style={{ width: 'auto', height: 44 }}>
      <motion.div
        ref={wrapperRef}
        data-panel
        className="absolute right-0 top-0 z-50 flex flex-col items-center overflow-hidden border border-brand-9/20"
        style={{ background: "#080c12", boxShadow: "0 8px 40px rgba(0,0,0,0.85), 0 0 30px rgba(0,44,124,0.2)" }}
        initial={false}
        animate={{
          width: showForm ? FORM_WIDTH : "auto",
          height: showForm ? "auto" : 44,
          borderRadius: showForm ? 14 : 20,
        }}
        transition={{
          type: "spring",
          stiffness: 550 / SPEED_FACTOR,
          damping: 45,
          mass: 0.7,
          delay: showForm ? 0 : 0.08,
        }}
      >
        <FormContext.Provider value={ctx}>
          <DockBar neighborhoodName={neighborhoodName} />
          <InputForm
            ref={textareaRef}
            onSuccess={handleSuccess}
            onClearResponse={() => setResponse("")}
            response={response}
            loading={loading}
            responseRef={responseRef}
            neighborhoodName={neighborhoodName}
          />
        </FormContext.Provider>
      </motion.div>
    </div>
  )
}

function DockBar({ neighborhoodName }: { neighborhoodName?: string }) {
  const { showForm, triggerOpen } = useFormContext()
  return (
    <footer className="mt-auto flex h-[44px] items-center justify-center whitespace-nowrap select-none">
      <div className="flex items-center justify-center gap-2 px-3 max-sm:h-10 max-sm:px-2">
        <div className="flex w-fit items-center gap-2">
          <AnimatePresence mode="wait">
            {showForm ? (
              <motion.div key="blank" initial={{ opacity: 0 }} animate={{ opacity: 0 }} exit={{ opacity: 0 }} className="h-5 w-5" />
            ) : (
              <motion.div key="orb" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }}>
                <ColorOrb
                  dimension="24px"
                  tones={{
                    base: "oklch(22.64% 0 0)",
                    accent1: "#002c7c",
                    accent2: "#007260",
                    accent3: "#2ad587",
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <Button
          type="button"
          className="flex h-fit flex-1 justify-end rounded-full px-2 !py-0.5 text-white/70 hover:text-white"
          variant="ghost"
          onClick={triggerOpen}
        >
          <AnthropicDark className="w-3.5 h-3.5 mr-1.5 text-brand-9" />
          <span className="truncate text-sm">
            {neighborhoodName ? `Ask about ${neighborhoodName}` : "Ask AI"}
          </span>
        </Button>
      </div>
    </footer>
  )
}

interface InputFormProps {
  ref: React.Ref<HTMLTextAreaElement>
  onSuccess: (message: string) => void
  onClearResponse: () => void
  response: string
  loading: boolean
  responseRef: React.RefObject<HTMLDivElement | null>
  neighborhoodName?: string
}

function InputForm({ ref, onSuccess, onClearResponse, response, loading, responseRef, neighborhoodName }: InputFormProps) {
  const { triggerClose, showForm } = useFormContext()
  const btnRef = React.useRef<HTMLButtonElement>(null)

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const data = new FormData(form)
    const message = data.get("message") as string
    if (message?.trim()) {
      onSuccess(message)
    }
  }

  function handleKeys(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Escape") triggerClose()
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      btnRef.current?.click()
    }
  }

  const placeholder = neighborhoodName
    ? `Ask about ${neighborhoodName}...`
    : "Ask about any neighborhood..."

  return (
    <form
      onSubmit={handleSubmit}
      className="relative w-full"
      style={{ pointerEvents: showForm ? "all" : "none" }}
    >
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ type: "spring", stiffness: 550 / SPEED_FACTOR, damping: 45, mass: 0.7 }}
            className="flex h-full flex-col p-1"
          >
            <div className="flex justify-between py-1 items-center">
              <div className="z-2 ml-[38px] flex items-center gap-[6px] select-none">
                <AnthropicDark className="w-3.5 h-3.5 text-brand-9" />
                <span className="text-sm font-semibold text-white">AI Assistant</span>
                {neighborhoodName && (
                  <span className="text-[11px] text-white/40 font-mono ml-1">· {neighborhoodName}</span>
                )}
              </div>
              <div className="flex items-center gap-1 mr-1">
                <button
                  type="submit"
                  ref={btnRef}
                  disabled={loading}
                  className="flex cursor-pointer items-center justify-center gap-1 rounded-xl bg-brand-9/15 text-brand-9 px-2 py-1 hover:bg-brand-9/25 transition disabled:opacity-40"
                >
                  {loading ? (
                    <div className="w-4 h-0.5 rounded-full bg-brand-9/20 overflow-hidden">
                      <div className="h-full w-[200%] bg-brand-9" style={{ animation: 'ai-slide 0.8s linear infinite' }} />
                      <style>{`@keyframes ai-slide { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }`}</style>
                    </div>
                  ) : (
                    <Send size={14} />
                  )}
                </button>
                <button
                  type="button"
                  onClick={triggerClose}
                  className="flex cursor-pointer items-center justify-center rounded-xl p-1.5 text-white/40 hover:text-white/80 hover:bg-white/[0.06] transition"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
            {!response && (
              <textarea
                ref={ref}
                placeholder={placeholder}
                name="message"
                className="h-[120px] w-full resize-none scroll-py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] p-3 text-sm text-white placeholder:text-white/30 outline-0 focus:border-brand-9/30 transition-colors"
                required
                onKeyDown={handleKeys}
                spellCheck={false}
              />
            )}

            {/* Response area */}
            {response && (
              <div
                ref={responseRef}
                className="mt-2 max-h-[300px] overflow-y-auto scrollbar-thin rounded-xl bg-white/[0.02] border border-white/[0.06] p-3 relative"
              >
                <button
                  type="button"
                  onClick={() => { onClearResponse(); }}
                  className="absolute top-2 right-2 p-1 rounded-md text-white/30 hover:text-white/70 hover:bg-white/[0.06] transition-colors"
                >
                  <X size={12} />
                </button>
                <div className="flex gap-2.5 pr-5">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-5 h-5 rounded-full flex items-center justify-center bg-brand-9/10 border border-brand-9/15">
                      <AnthropicDark className="w-3 h-3 text-brand-9" />
                    </div>
                  </div>
                  <div
                    className="ai-response-md text-[13px] text-white leading-[1.7] flex-1 min-w-0"
                    dangerouslySetInnerHTML={{ __html: marked.parse(response, { async: false }) as string }}
                  />
                </div>
              </div>
            )}

            {/* Follow-up input */}
            {response && (
              <div className="mt-2 flex items-center gap-2">
                <textarea
                  ref={ref}
                  placeholder="Ask a follow-up..."
                  name="message"
                  className="flex-1 h-[40px] resize-none rounded-lg bg-white/[0.04] border border-white/[0.08] px-3 py-2 text-sm text-white placeholder:text-white/30 outline-0 focus:border-brand-9/30 transition-colors"
                  onKeyDown={handleKeys}
                  spellCheck={false}
                  required
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="flex cursor-pointer items-center justify-center rounded-lg bg-brand-9/15 text-brand-9 p-2 hover:bg-brand-9/25 transition disabled:opacity-40"
                >
                  {loading ? (
                    <div className="w-4 h-4 rounded-full border-2 border-brand-9/20 border-t-brand-9 animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute top-2 left-3"
          >
            <ColorOrb
              dimension="24px"
              tones={{
                base: "oklch(22.64% 0 0)",
                accent1: "#002c7c",
                accent2: "#007260",
                accent3: "#2ad587",
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </form>
  )
}

export default MorphPanel

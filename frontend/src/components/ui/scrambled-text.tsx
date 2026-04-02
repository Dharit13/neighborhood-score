import { useEffect, useRef, useState } from 'react'

const SCRAMBLE_CHARS = '!<>-_\\/[]{}—=+*^?#ABCDEFGHIJKLMNOPQRSTUVWXYZ'

interface ScrambledTextProps {
  text: string
  className?: string
  /** Class applied only after the scramble animation completes (e.g. gradient-text) */
  resolvedClassName?: string
  /** Trigger scramble when element enters viewport. Default true */
  triggerOnView?: boolean
}

export default function ScrambledText({ text, className, resolvedClassName, triggerOnView = true }: ScrambledTextProps) {
  const elRef = useRef<HTMLSpanElement>(null)
  const hasAnimated = useRef(false)
  const rafRef = useRef<number>(0)
  const [displayHTML, setDisplayHTML] = useState('')
  const [resolved, setResolved] = useState(false)

  useEffect(() => {
    hasAnimated.current = false
    setDisplayHTML('')
    setResolved(false)
    cancelAnimationFrame(rafRef.current)

    if (!elRef.current) return

    if (!triggerOnView) {
      startScramble()
      return () => cancelAnimationFrame(rafRef.current)
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true
          startScramble()
        }
      },
      { threshold: 0.2 },
    )
    observer.observe(elRef.current)
    return () => {
      observer.disconnect()
      cancelAnimationFrame(rafRef.current)
    }
  }, [text, triggerOnView])

  function startScramble() {
    const length = text.length
    const queue: Array<{ from: string; to: string; start: number; end: number; char?: string }> = []

    for (let i = 0; i < length; i++) {
      const start = Math.floor(Math.random() * 40)
      const end = start + Math.floor(Math.random() * 40)
      queue.push({ from: '', to: text[i], start, end })
    }

    let frame = 0

    function update() {
      let output = ''
      let complete = 0

      for (let i = 0; i < queue.length; i++) {
        const { to, start, end } = queue[i]
        let { char } = queue[i]

        if (frame >= end) {
          complete++
          output += to
        } else if (frame >= start) {
          if (!char || Math.random() < 0.28) {
            char = SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)]
            queue[i].char = char
          }
          output += `<span style="color:#0f0;opacity:0.7">${char}</span>`
        }
      }

      setDisplayHTML(output)

      if (complete === queue.length) {
        setResolved(true)
        return
      }
      frame++
      rafRef.current = requestAnimationFrame(update)
    }

    rafRef.current = requestAnimationFrame(update)
  }

  const classes = [className, resolved && resolvedClassName].filter(Boolean).join(' ') || undefined

  return (
    <span
      ref={elRef}
      className={classes}
      dangerouslySetInnerHTML={{ __html: displayHTML }}
    />
  )
}

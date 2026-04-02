import { useState, useEffect, useCallback } from "react"

interface Character {
  char: string
  x: number
  y: number
  speed: number
}

const ALL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:,.<>?"

interface RainingLettersProps {
  className?: string
  charCount?: number
  /** Overall opacity of the effect (0-1). Default 0.8 */
  opacity?: number
}

export default function RainingLetters({ className, charCount = 300, opacity = 0.8 }: RainingLettersProps) {
  const [characters, setCharacters] = useState<Character[]>([])
  const [activeIndices, setActiveIndices] = useState<Set<number>>(new Set())

  const createCharacters = useCallback(() => {
    const newCharacters: Character[] = []
    for (let i = 0; i < charCount; i++) {
      newCharacters.push({
        char: ALL_CHARS[Math.floor(Math.random() * ALL_CHARS.length)],
        x: Math.random() * 100,
        y: Math.random() * 100,
        speed: 0.1 + Math.random() * 0.3,
      })
    }
    return newCharacters
  }, [charCount])

  useEffect(() => {
    setCharacters(createCharacters())
  }, [createCharacters])

  useEffect(() => {
    const updateActiveIndices = () => {
      const newActiveIndices = new Set<number>()
      const numActive = Math.floor(Math.random() * 3) + 3
      for (let i = 0; i < numActive; i++) {
        newActiveIndices.add(Math.floor(Math.random() * characters.length))
      }
      setActiveIndices(newActiveIndices)
    }

    const flickerInterval = setInterval(updateActiveIndices, 50)
    return () => clearInterval(flickerInterval)
  }, [characters.length])

  useEffect(() => {
    let animationFrameId: number

    const updatePositions = () => {
      setCharacters(prevChars =>
        prevChars.map(char => ({
          ...char,
          y: char.y + char.speed,
          ...(char.y >= 100 && {
            y: -5,
            x: Math.random() * 100,
            char: ALL_CHARS[Math.floor(Math.random() * ALL_CHARS.length)],
          }),
        }))
      )
      animationFrameId = requestAnimationFrame(updatePositions)
    }

    animationFrameId = requestAnimationFrame(updatePositions)
    return () => cancelAnimationFrame(animationFrameId)
  }, [])

  return (
    <div className={className} style={{ opacity }}>
      {characters.map((char, index) => {
        const isActive = activeIndices.has(index)
        return (
          <span
            key={index}
            className={`absolute pointer-events-none select-none ${
              isActive
                ? "text-[#00ff00] font-bold animate-pulse z-10"
                : "text-slate-600 font-light"
            }`}
            style={{
              left: `${char.x}%`,
              top: `${char.y}%`,
              transform: `translate(-50%, -50%) ${isActive ? 'scale(1.25)' : 'scale(1)'}`,
              textShadow: isActive
                ? '0 0 8px rgba(255,255,255,0.8), 0 0 12px rgba(255,255,255,0.4)'
                : 'none',
              opacity: isActive ? 1 : 0.4,
              transition: 'color 0.1s, transform 0.1s, text-shadow 0.1s',
              willChange: 'transform, top',
              fontSize: '1.8rem',
            }}
          >
            {char.char}
          </span>
        )
      })}
    </div>
  )
}

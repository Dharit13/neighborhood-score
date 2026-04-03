"use client"

import { useState, useEffect, useCallback, useRef } from "react"

const TETRIS_PIECES_DARK = [
  { shape: [[1, 1, 1, 1]], color: 'bg-brand-1' },
  { shape: [[1, 1], [1, 1]], color: 'bg-brand-9' },
  { shape: [[0, 1, 0], [1, 1, 1]], color: 'bg-brand-5' },
  { shape: [[1, 0], [1, 0], [1, 1]], color: 'bg-brand-3' },
  { shape: [[0, 1, 1], [1, 1, 0]], color: 'bg-brand-7' },
  { shape: [[1, 1, 0], [0, 1, 1]], color: 'bg-brand-8' },
  { shape: [[0, 1], [0, 1], [1, 1]], color: 'bg-brand-2' },
]

const TETRIS_PIECES_LIGHT = [
  { shape: [[1, 1, 1, 1]], color: 'bg-[#b91c1c]' },
  { shape: [[1, 1], [1, 1]], color: 'bg-[#1a1a1a]' },
  { shape: [[0, 1, 0], [1, 1, 1]], color: 'bg-[#a09888]' },
  { shape: [[1, 0], [1, 0], [1, 1]], color: 'bg-[#8a8a8a]' },
  { shape: [[0, 1, 1], [1, 1, 0]], color: 'bg-[#d0c8b8]' },
  { shape: [[1, 1, 0], [0, 1, 1]], color: 'bg-[#4a4a4a]' },
  { shape: [[0, 1], [0, 1], [1, 1]], color: 'bg-[#b91c1c]/70' },
]

// Compare section uses indigo/blue palette
const TETRIS_PIECES_COMPARE = [
  { shape: [[1, 1, 1, 1]], color: 'bg-indigo-500' },
  { shape: [[1, 1], [1, 1]], color: 'bg-blue-400' },
  { shape: [[0, 1, 0], [1, 1, 1]], color: 'bg-indigo-400' },
  { shape: [[1, 0], [1, 0], [1, 1]], color: 'bg-violet-500' },
  { shape: [[0, 1, 1], [1, 1, 0]], color: 'bg-blue-500' },
  { shape: [[1, 1, 0], [0, 1, 1]], color: 'bg-indigo-300' },
  { shape: [[0, 1], [0, 1], [1, 1]], color: 'bg-violet-400' },
]

interface Cell {
  filled: boolean
  color: string
}

interface FallingPiece {
  shape: number[][]
  color: string
  x: number
  y: number
  id: string
}

export interface TetrisLoadingProps {
  size?: 'sm' | 'md' | 'lg'
  speed?: 'slow' | 'normal' | 'fast'
  showLoadingText?: boolean
  loadingText?: string
  variant?: 'dark' | 'light' | 'compare'
}

export default function TetrisLoading({
  size = 'md',
  speed = 'normal',
  showLoadingText = true,
  loadingText = 'Loading...',
  variant = 'dark',
}: TetrisLoadingProps) {
  const pieces = variant === 'light' ? TETRIS_PIECES_LIGHT : variant === 'compare' ? TETRIS_PIECES_COMPARE : TETRIS_PIECES_DARK
  const isLight = variant === 'light'
  const sizeConfig = {
    sm: { cellSize: 'w-2 h-2', gridWidth: 8, gridHeight: 16, padding: 'p-0.5' },
    md: { cellSize: 'w-3 h-3', gridWidth: 10, gridHeight: 20, padding: 'p-1' },
    lg: { cellSize: 'w-4 h-4', gridWidth: 10, gridHeight: 20, padding: 'p-1.5' }
  }

  const speedConfig = {
    slow: 150,
    normal: 80,
    fast: 40
  }

  const config = sizeConfig[size]
  const fallSpeed = speedConfig[speed]

  const [grid, setGrid] = useState<Cell[][]>(() =>
    Array(config.gridHeight).fill(null).map(() => 
      Array(config.gridWidth).fill(null).map(() => ({ filled: false, color: '' }))
    )
  )
  const [fallingPiece, setFallingPiece] = useState<FallingPiece | null>(null)
  const [isClearing, setIsClearing] = useState(false)
  const frameRef = useRef<number>(undefined)
  const lastUpdateRef = useRef<number>(0)

  const rotateShape = useCallback((shape: number[][]): number[][] => {
    const rows = shape.length
    const cols = shape[0].length
    const rotated: number[][] = Array(cols).fill(null).map(() => Array(rows).fill(0))

    for (let i = 0; i < rows; i++) {
      for (let j = 0; j < cols; j++) {
        rotated[j][rows - 1 - i] = shape[i][j]
      }
    }

    return rotated
  }, [])

  const createNewPiece = useCallback((): FallingPiece => {
    const pieceData = pieces[Math.floor(Math.random() * pieces.length)]
    let shape = pieceData.shape
    
    const rotations = Math.floor(Math.random() * 4)
    for (let i = 0; i < rotations; i++) {
      shape = rotateShape(shape)
    }

    const maxX = config.gridWidth - shape[0].length
    const x = Math.floor(Math.random() * (maxX + 1))

    return {
      shape,
      color: pieceData.color,
      x,
      y: -shape.length,
      id: Math.random().toString(36).substr(2, 9),
    }
  }, [rotateShape, config.gridWidth, pieces])

  const canPlacePiece = useCallback((piece: FallingPiece, newX: number, newY: number): boolean => {
    for (let row = 0; row < piece.shape.length; row++) {
      for (let col = 0; col < piece.shape[row].length; col++) {
        if (piece.shape[row][col]) {
          const gridX = newX + col
          const gridY = newY + row

          if (gridX < 0 || gridX >= config.gridWidth || gridY >= config.gridHeight) {
            return false
          }

          if (gridY >= 0 && grid[gridY][gridX].filled) {
            return false
          }
        }
      }
    }
    return true
  }, [grid, config.gridWidth, config.gridHeight])

  const placePiece = useCallback((piece: FallingPiece) => {
    setGrid(prevGrid => {
      const newGrid = prevGrid.map(row => row.map(cell => ({ ...cell })))

      for (let row = 0; row < piece.shape.length; row++) {
        for (let col = 0; col < piece.shape[row].length; col++) {
          if (piece.shape[row][col]) {
            const gridX = piece.x + col
            const gridY = piece.y + row

            if (gridY >= 0 && gridY < config.gridHeight && gridX >= 0 && gridX < config.gridWidth) {
              newGrid[gridY][gridX] = { filled: true, color: piece.color }
            }
          }
        }
      }

      return newGrid
    })
  }, [config.gridHeight, config.gridWidth])

  const clearFullLines = useCallback(() => {
    setGrid(prevGrid => {
      const linesToClear: number[] = []
      
      prevGrid.forEach((row, index) => {
        if (row.every(cell => cell.filled)) {
          linesToClear.push(index)
        }
      })

      if (linesToClear.length > 0) {
        setIsClearing(true)
        
        const newGrid = prevGrid.map((row, rowIndex) => {
          if (linesToClear.includes(rowIndex)) {
            return row.map(cell => ({ ...cell, color: 'bg-brand-9 animate-pulse opacity-50' }))
          }
          return row
        })

        setTimeout(() => {
          setGrid(currentGrid => {
            const filteredGrid = currentGrid.filter((_, index) => !linesToClear.includes(index))
            const emptyRows = Array(linesToClear.length).fill(null).map(() => 
              Array(config.gridWidth).fill(null).map(() => ({ filled: false, color: '' }))
            )
            setIsClearing(false)
            return [...emptyRows, ...filteredGrid]
          })
        }, 200)

        return newGrid
      }

      return prevGrid
    })
  }, [config.gridWidth])

  const checkAndReset = useCallback(() => {
    const topRows = grid.slice(0, 4)
    const needsReset = topRows.some(row => row.filter(cell => cell.filled).length > config.gridWidth * 0.7)

    if (needsReset) {
      setIsClearing(true)
      setTimeout(() => {
        setGrid(Array(config.gridHeight).fill(null).map(() => 
          Array(config.gridWidth).fill(null).map(() => ({ filled: false, color: '' }))
        ))
        setFallingPiece(null)
        setIsClearing(false)
      }, 500)
      return true
    }
    return false
  }, [grid, config.gridWidth, config.gridHeight])

  useEffect(() => {
    const gameLoop = (timestamp: number) => {
      if (timestamp - lastUpdateRef.current >= fallSpeed) {
        lastUpdateRef.current = timestamp

        if (!isClearing && !checkAndReset()) {
          setFallingPiece(prevPiece => {
            if (!prevPiece) {
              return createNewPiece()
            }

            const newY = prevPiece.y + 1

            if (canPlacePiece(prevPiece, prevPiece.x, newY)) {
              return { ...prevPiece, y: newY }
            } else {
              placePiece(prevPiece)
              setTimeout(clearFullLines, 50)
              return createNewPiece()
            }
          })
        }
      }

      frameRef.current = requestAnimationFrame(gameLoop)
    }

    frameRef.current = requestAnimationFrame(gameLoop)

    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current)
      }
    }
  }, [canPlacePiece, createNewPiece, placePiece, clearFullLines, checkAndReset, isClearing, fallSpeed])

  const renderGrid = () => {
    const displayGrid = grid.map(row => row.map(cell => ({ ...cell })))

    if (fallingPiece && !isClearing) {
      for (let row = 0; row < fallingPiece.shape.length; row++) {
        for (let col = 0; col < fallingPiece.shape[row].length; col++) {
          if (fallingPiece.shape[row][col]) {
            const gridX = fallingPiece.x + col
            const gridY = fallingPiece.y + row

            if (gridY >= 0 && gridY < config.gridHeight && gridX >= 0 && gridX < config.gridWidth) {
              displayGrid[gridY][gridX] = { filled: true, color: fallingPiece.color }
            }
          }
        }
      }
    }

    return displayGrid.map((row, rowIndex) => (
      <div key={rowIndex} className="flex">
        {row.map((cell, colIndex) => (
          <div
            key={`${rowIndex}-${colIndex}`}
            className={`${config.cellSize} border transition-all duration-100 ${
              isLight ? 'border-[#d0c8b8]/40' : 'border-white/[0.06]'
            } ${
              cell.filled
                ? `${cell.color} scale-100`
                : isLight ? 'bg-[#e8e0d0]/30 scale-95' : 'bg-white/[0.04] scale-95'
            } ${isClearing && rowIndex < 4 ? 'animate-pulse' : ''}`}
          />
        ))}
      </div>
    ))
  }

  return (
    <div className="flex flex-col items-center">
      <div className="mb-4">
        <div className={`inline-block border backdrop-blur-md rounded-xl ${config.padding} transition-colors ${
          isLight ? 'border-[#d0c8b8] bg-white/40' : 'border-white/[0.10] bg-black/70'
        }`}>
          {renderGrid()}
        </div>
      </div>

      {showLoadingText && (
        <p className={`font-medium text-sm transition-colors ${isLight ? 'text-[#4a4a4a]' : 'text-white/70'}`}>{loadingText}</p>
      )}
    </div>
  )
}

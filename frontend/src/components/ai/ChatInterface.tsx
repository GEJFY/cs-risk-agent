'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

/** メッセージ型 */
interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  provider?: string
  model?: string
}

interface ChatInterfaceProps {
  /** カードタイトル */
  title?: string
  /** AIプロバイダー */
  provider?: string
  /** モデルティア */
  tier?: string
  /** 企業ID（コンテキスト用） */
  companyId?: string
  /** カスタムクラス */
  className?: string
}

/**
 * AIチャットインターフェースコンポーネント
 * AIとの対話型インターフェースを提供する
 */
export function ChatInterface({
  title = 'AI アシスタント',
  provider,
  tier = 'cost_effective',
  companyId,
  className,
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        '連結子会社リスク分析AIアシスタントです。財務分析やリスク評価に関するご質問にお答えします。',
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  /** メッセージ表示領域のスクロール制御 */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  /** メッセージ送信処理 */
  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || isLoading) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8005'}/api/v1/ai/chat`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: trimmed,
            company_id: companyId || null,
            provider: provider || null,
            tier,
            stream: false,
          }),
        }
      )

      if (response.ok) {
        const data = await response.json()
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date(),
          provider: data.provider,
          model: data.model,
        }
        setMessages((prev) => [...prev, assistantMessage])
      } else {
        throw new Error(`API Error: ${response.status}`)
      }
    } catch (error) {
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        role: 'assistant',
        content: `申し訳ございません。応答の生成中にエラーが発生しました。${
          error instanceof Error ? error.message : ''
        }`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  /** Enter キー送信 */
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <Card className={cn('flex flex-col', className)}>
      <CardHeader className="pb-3 border-b border-border">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-primary" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
      </CardHeader>

      {/* メッセージエリア */}
      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar min-h-[300px] max-h-[500px]">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'flex gap-3 animate-fade-in',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            )}
          >
            {msg.role === 'assistant' && (
              <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                <Bot className="w-3.5 h-3.5 text-primary" />
              </div>
            )}
            <div
              className={cn(
                'max-w-[80%] rounded-xl px-4 py-2.5 text-sm',
                msg.role === 'user'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-foreground'
              )}
            >
              <p className="whitespace-pre-wrap leading-relaxed">
                {msg.content}
              </p>
              {msg.provider && (
                <p className="mt-1.5 text-xs opacity-60">
                  {msg.provider} / {msg.model}
                </p>
              )}
            </div>
            {msg.role === 'user' && (
              <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center shrink-0 mt-0.5">
                <User className="w-3.5 h-3.5 text-secondary-foreground" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3 animate-fade-in">
            <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5 text-primary" />
            </div>
            <div className="bg-muted rounded-xl px-4 py-3">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </CardContent>

      {/* 入力エリア */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="リスク分析について質問してください..."
            rows={1}
            className="flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2
              text-sm placeholder:text-muted-foreground
              focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="shrink-0"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  )
}

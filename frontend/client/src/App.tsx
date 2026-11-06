import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type User = { id: number; username: string }
type Chat = { id: number; title: string; created_at: string }
type Message = { id: number; chat_id: number; sender_id: number; sender_username: string; body: string; created_at: string }

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

async function api<T>(path: string, token?: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  })
  if (!response.ok) {
    const result = await response.json().catch(() => null)
    throw new Error(result?.detail || 'Не удалось выполнить запрос')
  }
  return response.json() as Promise<T>
}

const initials = (name: string) => name.slice(0, 2).toUpperCase()
const timeLabel = (value: string) => new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value))

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('messenger-token') || '')
  const [user, setUser] = useState<User | null>(null)
  const [chats, setChats] = useState<Chat[]>([])
  const [activeChat, setActiveChat] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [search, setSearch] = useState('')
  const [draft, setDraft] = useState('')
  const [chatTitle, setChatTitle] = useState('')
  const [members, setMembers] = useState('')
  const [showNewChat, setShowNewChat] = useState(false)
  const [connection, setConnection] = useState<'connecting' | 'online' | 'offline'>('offline')
  const [error, setError] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  const messageEnd = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!token) return
    api<User>('/auth/me', token).then(setUser).catch(() => logout())
  }, [token])

  useEffect(() => {
    if (!token || !user) return
    api<Chat[]>('/chats', token).then((items) => {
      setChats(items)
      setActiveChat((current) => current ?? items[0]?.id ?? null)
    }).catch((reason: Error) => setError(reason.message))
  }, [token, user])

  useEffect(() => {
    if (!token || activeChat === null) return
    let cancelled = false
    let connectionSocket: WebSocket | null = null
    api<Message[]>(`/chats/${activeChat}/messages`, token).then((history) => {
      if (cancelled) return
      setMessages(history)
      const wsUrl = API_URL.replace(/^http/, 'ws')
      setConnection('connecting')
      connectionSocket = new WebSocket(`${wsUrl}/ws/chats/${activeChat}?token=${encodeURIComponent(token)}`)
      socket.current = connectionSocket
      connectionSocket.onopen = () => setConnection('online')
      connectionSocket.onclose = () => setConnection('offline')
      connectionSocket.onerror = () => setConnection('offline')
      connectionSocket.onmessage = (event) => {
        const incoming = JSON.parse(event.data) as Message | { error: string }
        if ('error' in incoming) { setError(incoming.error); return }
        setMessages((current) => [...current, incoming])
      }
    }).catch((reason: Error) => { if (!cancelled) setError(reason.message) })
    return () => {
      cancelled = true
      connectionSocket?.close()
      socket.current = null
      setConnection('offline')
    }
  }, [token, activeChat])

  useEffect(() => { messageEnd.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  function logout() {
    localStorage.removeItem('messenger-token')
    setToken(''); setUser(null); setChats([]); setMessages([]); setActiveChat(null)
    socket.current?.close()
  }

  async function handleAuth(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    try {
      if (authMode === 'register') {
        await api('/auth/register', undefined, { method: 'POST', body: JSON.stringify({ username, password }) })
      }
      const result = await api<{ access_token: string }>('/auth/login', undefined, {
        method: 'POST', body: JSON.stringify({ username, password }),
      })
      localStorage.setItem('messenger-token', result.access_token)
      setToken(result.access_token); setPassword('')
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось войти') }
  }

  async function handleCreateChat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('')
    try {
      const created = await api<Chat>('/chats', token, {
        method: 'POST',
        body: JSON.stringify({ title: chatTitle.trim() || 'Новый чат', member_usernames: members.split(',').map((name) => name.trim()).filter(Boolean) }),
      })
      setChats((current) => [created, ...current]); setMessages([]); setActiveChat(created.id); setConnection('connecting')
      setChatTitle(''); setMembers(''); setShowNewChat(false); setSidebarOpen(false)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Не удалось создать чат') }
  }

  function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const body = draft.trim()
    if (!body || socket.current?.readyState !== WebSocket.OPEN) return
    socket.current.send(JSON.stringify({ body })); setDraft('')
  }

  const visibleChats = useMemo(() => chats.filter((chat) => chat.title.toLowerCase().includes(search.toLowerCase())), [chats, search])
  const selectedChat = chats.find((chat) => chat.id === activeChat)

  if (!token || !user) return (
    <main className="auth-page">
      <section className="auth-art">
        <div className="brand brand-light"><span className="brand-mark">m</span> melo</div>
        <div className="auth-art-copy"><span className="eyebrow">ПРОСТРАНСТВО ДЛЯ ДИАЛОГА</span><h1>Мысль звучит лучше, когда ею делятся.</h1><p>Личные и групповые чаты в одном спокойном месте.</p></div>
        <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
        <div className="art-note note-one">на связи</div><div className="art-note note-two">всё важное рядом</div>
        <div className="auth-art-foot"><span>01</span><span>Честный разговор начинается здесь</span></div>
      </section>
      <section className="auth-panel">
        <div className="auth-topline"><span>WEB MESSENGER</span><span>ПМ01 · MVP</span></div>
        <form className="auth-form" onSubmit={handleAuth}>
          <span className="eyebrow">{authMode === 'login' ? 'С ВОЗВРАЩЕНИЕМ' : 'СОЗДАТЬ АККАУНТ'}</span>
          <h2>{authMode === 'login' ? 'Войти в мессенджер' : 'Начать общение'}</h2>
          <p className="form-intro">{authMode === 'login' ? 'Введите данные своего аккаунта.' : 'Зарегистрируйтесь, чтобы создать первый чат.'}</p>
          <label>Имя пользователя<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" minLength={3} required /></label>
          <label>Пароль<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} minLength={authMode === 'login' ? 1 : 8} required /></label>
          {error && <div className="inline-error">{error}</div>}
          <button className="primary-button" type="submit">{authMode === 'login' ? 'Войти' : 'Зарегистрироваться'}<span>↗</span></button>
          <p className="switch-mode">{authMode === 'login' ? 'Впервые здесь?' : 'Уже есть аккаунт?'}{' '}<button type="button" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError('') }}>{authMode === 'login' ? 'Создать аккаунт' : 'Войти'}</button></p>
        </form>
        <div className="auth-foot"><span>© 2026 MELO MESSENGER</span><span>СОЗДАН ДЛЯ ОБЩЕНИЯ</span></div>
      </section>
    </main>
  )

  return (
    <main className={`messenger-shell ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-head"><div className="brand"><span className="brand-mark">m</span> melo</div><button className="icon-button" type="button" onClick={() => setShowNewChat((open) => !open)} aria-label="Создать чат">＋</button></div>
        <div className="sidebar-label"><span>ВАШИ ДИАЛОГИ</span><span>{String(chats.length).padStart(2, '0')}</span></div>
        <label className="search-box"><span>⌕</span><input aria-label="Поиск чатов" placeholder="Найти разговор" value={search} onChange={(event) => setSearch(event.target.value)} /><kbd>⌘ K</kbd></label>
        {showNewChat && <form className="new-chat-form" onSubmit={handleCreateChat}><div className="new-chat-title">Новый разговор</div><input placeholder="Название чата" value={chatTitle} onChange={(event) => setChatTitle(event.target.value)} maxLength={100} /><input placeholder="Участники через запятую" value={members} onChange={(event) => setMembers(event.target.value)} /><button className="primary-button" type="submit">Создать чат <span>↗</span></button></form>}
        <div className="chat-list">
          {visibleChats.map((chat, index) => {
            const lastMessage = messages.filter((message) => message.chat_id === chat.id).slice(-1)[0]
            return <button className={`chat-item ${activeChat === chat.id ? 'active' : ''}`} key={chat.id} onClick={() => { setMessages([]); setActiveChat(chat.id); setConnection('connecting'); setSidebarOpen(false) }}>
              <span className={`avatar avatar-${index % 4}`}>{initials(chat.title)}</span><span className="chat-item-copy"><span className="chat-item-title">{chat.title}</span><span className="chat-item-preview">{lastMessage?.body || 'Начните разговор'}</span></span><span className="chat-item-time">{lastMessage ? timeLabel(lastMessage.created_at) : ''}</span>
            </button>
          })}
          {visibleChats.length === 0 && <div className="empty-sidebar">{chats.length ? 'Ничего не найдено' : 'Пока нет чатов. Создайте первый.'}</div>}
        </div>
        <div className="sidebar-footer"><div className="profile-card"><span className="avatar avatar-profile">{initials(user.username)}</span><span className="profile-copy"><strong>{user.username}</strong><small>Личный аккаунт</small></span><button type="button" className="logout-button" onClick={logout} title="Выйти">↗</button></div><span className="sidebar-version">MELO MESSENGER <span>v0.4</span></span></div>
      </aside>
      <section className="conversation">
        <header className="conversation-header">
          <button className="mobile-menu-button" type="button" onClick={() => setSidebarOpen(true)} aria-label="Открыть список чатов">☰</button>
          {selectedChat ? <><span className="avatar avatar-header">{initials(selectedChat.title)}</span><div className="conversation-title"><h2>{selectedChat.title}</h2><span><i className={`status-dot ${connection}`} />{connection === 'online' ? 'в сети' : connection === 'connecting' ? 'подключение…' : 'не в сети'}</span></div><div className="header-actions"><button type="button" aria-label="Поиск">⌕</button><button type="button" aria-label="Ещё">···</button></div></> : <div className="conversation-title"><h2>Ваши сообщения</h2><span>Выберите чат или начните новый</span></div>}
        </header>
        <div className="message-area">
          {selectedChat ? <><div className="day-divider"><span /><p>НАЧАЛО РАЗГОВОРА</p><span /></div>
            {messages.length === 0 ? <div className="conversation-empty"><span className="empty-symbol">m</span><h3>Здесь начинается разговор</h3><p>Напишите первое сообщение в чате «{selectedChat.title}».</p></div> : messages.map((message) => {
              const mine = message.sender_id === user.id
              return <div className={`message-row ${mine ? 'mine' : ''}`} key={message.id}>{!mine && <span className="avatar avatar-message">{initials(message.sender_username)}</span>}<div className="message-content">{!mine && <span className="message-author">{message.sender_username}</span>}<div className="message-bubble">{message.body}</div><span className="message-time">{timeLabel(message.created_at)}{mine && <b> ✓</b>}</span></div></div>
          })}<div ref={messageEnd} /></> : <div className="conversation-empty no-chat"><span className="empty-symbol">m</span><h3>Ваше пространство для общения</h3><p>Создайте чат, чтобы начать переписку.</p><button className="primary-button" type="button" onClick={() => { setShowNewChat(true); setSidebarOpen(true) }}>Создать чат <span>↗</span></button></div>}
        </div>
        {error && <div className="toast-error"><span>{error}</span><button onClick={() => setError('')} aria-label="Закрыть">×</button></div>}
        {selectedChat && <form className="composer" onSubmit={sendMessage}><button className="composer-plus" type="button" aria-label="Добавить вложение" disabled>＋</button><input placeholder="Напишите сообщение…" value={draft} onChange={(event) => setDraft(event.target.value)} disabled={connection !== 'online'} /><span className="composer-hint">Enter для отправки</span><button className="send-button" type="submit" disabled={!draft.trim() || connection !== 'online'} aria-label="Отправить сообщение">↗</button></form>}
      </section>
    </main>
  )
}

export default App

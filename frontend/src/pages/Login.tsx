import React, { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

function Login() {
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await api.post('/auth/login', {
                username,
                password
            })
            localStorage.setItem('token', res.data.access_token)
            const requestedPath = searchParams.get('next')
            const destination =
                requestedPath?.startsWith('/') && !requestedPath.startsWith('//')
                    ? requestedPath
                    : '/'
            navigate(destination, { replace: true })
        } catch (err) {
            setError(messageFrom(err))
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="login-page">
            <a href="/" className="brand">
                <span>BOOK</span><i>•</i><span>IT</span>
            </a>

            <div className="login-card">
                <p className="kicker">WELCOME BACK</p>
                <h1>
                    Your campus,<br />
                    <em>ready when you are.</em>
                </h1>

                {error && <p className="notice">{error}</p>}

                <form onSubmit={handleLogin} className="form-grid">
                    <label className="wide">
                        Username
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            autoComplete="username"
                            disabled={loading}
                        />
                    </label>

                    <label className="wide">
                        Password
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            autoComplete="current-password"
                            disabled={loading}
                        />
                    </label>

                    <button type="submit" className="primary wide" disabled={loading}>
                        {loading ? 'Signing in...' : 'Enter Book-It'}
                    </button>
                </form>
            </div>
        </div>
    )
}

export default Login
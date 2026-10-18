
import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { api, messageFrom } from '../lib/api'

function Login() {
    const [isRegistering, setIsRegistering] = useState(false)
    const [fullName, setFullName] = useState('')
    const [email, setEmail] = useState('')
    const [username, setUsername] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()
    useEffect(() => {
        if (!localStorage.getItem('token')) return
        api.get('/auth/me').then(() => {
            const requestedPath = searchParams.get('next')
            const destination =
                requestedPath?.startsWith('/') && !requestedPath.startsWith('//')
                    ? requestedPath
                    : '/'
            navigate(destination, { replace: true })
        }).catch(() => {
            localStorage.removeItem('token')
            localStorage.removeItem('refresh_token')
        })
    }, [navigate, searchParams])
    const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault()
        setError('')
        setNotice('')
        setLoading(true)

        try {
            if (isRegistering) {
                await api.post('/auth/register', {
                    username: username.trim(),
                    email: email.trim(),
                    password,
                    full_name: fullName.trim() || undefined
                })

                setIsRegistering(false)
                setPassword('')
                setNotice('Account created successfully. Sign in with your username and password.')
                return
            }

            const res = await api.post('/auth/login', {
                username: username.trim(),
                password
            })

            localStorage.setItem('token', res.data.access_token)
            localStorage.setItem('refresh_token', res.data.refresh_token)

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

    const switchMode = () => {
        setIsRegistering(!isRegistering)
        setError('')
        setNotice('')
    }

    return (
        <div className="login-page">
            <a href="/" className="brand">
                <span>BOOK</span><i>•</i><span>IT</span>
            </a>

            <div className="login-card">
                <p className="kicker">
                    {isRegistering ? 'JOIN BOOK-IT' : 'WELCOME BACK'}
                </p>

                <h1>
                    {isRegistering ? (
                        <>Make room<br /><em>for what’s next.</em></>
                    ) : (
                        <>Your campus,<br /><em>ready when you are.</em></>
                    )}
                </h1>

                {error && <p className="notice" role="alert">{error}</p>}
                {notice && <p className="notice" role="status">{notice}</p>}

                <form onSubmit={handleSubmit} className="form-grid">
                    {isRegistering && (
                        <>
                            <label className="wide">
                                Full name
                                <input
                                    type="text"
                                    value={fullName}
                                    onChange={e => setFullName(e.target.value)}
                                    autoComplete="name"
                                    disabled={loading}
                                />
                            </label>

                            <label className="wide">
                                Email
                                <input
                                    type="email"
                                    value={email}
                                    onChange={e => setEmail(e.target.value)}
                                    required
                                    autoComplete="email"
                                    disabled={loading}
                                />
                            </label>
                        </>
                    )}

                    <label className="wide">
                        Username
                        <input
                            type="text"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            required
                            autoComplete="username"
                            minLength={3}
                            disabled={loading}
                        />
                    </label>

                    <label className="wide">
                        Password
                        <input
                            type="password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            autoComplete={isRegistering ? 'new-password' : 'current-password'}
                            minLength={isRegistering ? 8 : undefined}
                            disabled={loading}
                        />
                    </label>

                    <button
                        type="submit"
                        className="primary wide"
                        disabled={loading}
                    >
                        {loading
                            ? (isRegistering ? 'Creating account...' : 'Signing in...')
                            : (isRegistering ? 'Create account' : 'Enter Book-It')}
                    </button>
                </form>

                <p style={{ textAlign: 'center', marginTop: 22, lineHeight: 1.5 }}>
                    {isRegistering
                        ? 'Already have an account? '
                        : 'New to Book-It? '}

                    <button
                        type="button"
                        onClick={switchMode}
                        disabled={loading}
                        style={{
                            border: 0,
                            padding: 0,
                            background: 'transparent',
                            color: 'var(--blue)',
                            font: 'inherit',
                            fontWeight: 700,
                            cursor: 'pointer',
                            textDecoration: 'underline'
                        }}
                    >
                        {isRegistering ? 'Sign in' : 'Create an account'}
                    </button>
                </p>
            </div>
        </div>
    )
}

export default Login

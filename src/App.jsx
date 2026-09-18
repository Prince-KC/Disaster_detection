import { useEffect, useMemo, useState } from 'react';
import { useAuth } from './context/AuthContext';
import {
  signInWithEmail,
  signInWithGoogle,
  signOutUser,
  signUpWithEmail,
} from './lib/supabase';

const REDIRECT_URL = `${window.location.origin}/#/dashboard`;

function getCurrentHashPath() {
  const hash = window.location.hash || '#/auth';
  return hash.startsWith('#') ? hash.slice(1) : hash;
}

function useCurrentRoute() {
  const [route, setRoute] = useState(getCurrentHashPath());

  useEffect(() => {
    const updateRoute = () => setRoute(getCurrentHashPath());
    window.addEventListener('hashchange', updateRoute);
    return () => window.removeEventListener('hashchange', updateRoute);
  }, []);

  return route;
}

function AuthScreen() {
  const { user, loading, error: authError, setError } = useAuth();
  const [mode, setMode] = useState('signin');
  const [form, setForm] = useState({ email: '', password: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (authError) {
      setFeedback(authError);
    }
  }, [authError]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const resetFeedback = () => {
    setFeedback('');
    setError('');
  };

  const handleEmailPasswordSubmit = async (event) => {
    event.preventDefault();
    resetFeedback();

    if (!form.email || !form.password) {
      setFeedback('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);

    try {
      if (mode === 'signup') {
        const { error } = await signUpWithEmail({
          email: form.email,
          password: form.password,
          redirectTo: REDIRECT_URL,
        });

        if (error) {
          throw error;
        }

        setFeedback('Account created. Please check your email to confirm your signup before signing in.');
        window.location.hash = '#/auth';
      } else {
        const { error } = await signInWithEmail({
          email: form.email,
          password: form.password,
        });

        if (error) {
          throw error;
        }

        setFeedback('Signed in successfully. Redirecting...');
        window.location.hash = '#/dashboard';
      }
    } catch (error) {
      setFeedback(error.message || 'Authentication failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = async () => {
    resetFeedback();
    setIsSubmitting(true);

    try {
      const { error } = await signInWithGoogle({ redirectTo: REDIRECT_URL });
      if (error) {
        throw error;
      }

      setFeedback('Redirecting to Google...');
    } catch (error) {
      setFeedback(error.message || 'Google sign-in failed.');
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <main className="auth-shell">
        <div className="status-card">
          <div className="spinner" aria-label="Loading" />
          <p>Loading your session...</p>
        </div>
      </main>
    );
  }

  if (user) {
    return <AuthenticatedApp user={user} />;
  }

  return (
    <main className="auth-shell">
      <div className="auth-card">
        <div className="brand-lockup">
          <div className="brand-mark">⌁</div>
          <div>
            <p className="eyebrow">Secure access</p>
            <h1>Innovision</h1>
          </div>
        </div>

        <div className="mode-toggle" role="tablist" aria-label="Authentication mode">
          <button
            type="button"
            className={mode === 'signin' ? 'active' : ''}
            onClick={() => {
              setMode('signin');
              resetFeedback();
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={mode === 'signup' ? 'active' : ''}
            onClick={() => {
              setMode('signup');
              resetFeedback();
            }}
          >
            Sign Up
          </button>
        </div>

        <form onSubmit={handleEmailPasswordSubmit} className="auth-form">
          <label>
            <span>Email</span>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="name@example.com"
              required
            />
          </label>

          <label>
            <span>Password</span>
            <div className="password-row">
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="Enter your password"
                minLength="6"
                required
              />
              <button type="button" className="ghost-button" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </label>

          {feedback ? <p className="feedback-banner">{feedback}</p> : null}

          <button className="primary-button" type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Please wait...' : mode === 'signup' ? 'Create account' : 'Sign In'}
          </button>
        </form>

        <div className="divider"><span>OR</span></div>

        <button type="button" className="google-button" onClick={handleGoogleLogin} disabled={isSubmitting}>
          <svg className="google-icon-svg" viewBox="0 0 24 24" width="20" height="20">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          Sign in with Google
        </button>
      </div>
    </main>
  );
}

function AuthenticatedApp({ user }) {
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [message, setMessage] = useState('');

  const handleSignOut = async () => {
    setIsSigningOut(true);
    setMessage('');

    try {
      const { error } = await signOutUser();
      if (error) {
        throw error;
      }
      window.location.hash = '#/auth';
    } catch (error) {
      setMessage(error.message || 'Unable to sign out.');
    } finally {
      setIsSigningOut(false);
    }
  };

  const welcomeName = useMemo(
    () => user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'User',
    [user]
  );

  return (
    <main className="dashboard-shell">
      <div className="dashboard-card">
        <p className="eyebrow">Authenticated</p>
        <h1>Welcome, {welcomeName}</h1>
        <p className="muted">You are signed in with Supabase Authentication.</p>
        <div className="user-meta">
          <span>{user?.email}</span>
          <span>{user?.email_confirmed_at ? 'Email confirmed' : 'Email pending confirmation'}</span>
        </div>
        {message ? <p className="feedback-banner error-banner">{message}</p> : null}
        <button type="button" className="primary-button" onClick={handleSignOut} disabled={isSigningOut}>
          {isSigningOut ? 'Signing out...' : 'Sign Out'}
        </button>
      </div>
    </main>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  const route = useCurrentRoute();

  useEffect(() => {
    if (loading) return;

    if (user && route !== '/dashboard') {
      window.location.hash = '#/dashboard';
      return;
    }

    if (!user && route === '/dashboard') {
      window.location.hash = '#/auth';
    }
  }, [loading, user, route]);

  if (!user && route === '/dashboard') {
    return <AuthScreen />;
  }

  return user ? <AuthenticatedApp user={user} /> : <AuthScreen />;
}

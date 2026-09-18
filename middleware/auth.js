/**
 * middleware/auth.js
 * JWT verification middleware for protected Express API routes.
 * Extracts Bearer token from Authorization header, verifies it,
 * and attaches decoded user payload to req.user.
 */

const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'khetrakshak_dev_secret_change_in_production';

/**
 * Middleware: requireAuth
 * Protects routes by verifying the JWT token in the Authorization header.
 * Usage: router.get('/protected', requireAuth, handler)
 */
function requireAuth(req, res, next) {
  const authHeader = req.headers['authorization'];

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({
      success: false,
      error: 'Unauthorized: No token provided.',
    });
  }

  const token = authHeader.split(' ')[1];

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded; // { id, email, name, role, iat, exp }
    next();
  } catch (err) {
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ success: false, error: 'Token expired. Please sign in again.' });
    }
    return res.status(401).json({ success: false, error: 'Invalid token.' });
  }
}

/**
 * Middleware: optionalAuth
 * Attaches user info if a valid token exists, but does NOT block the request.
 * Useful for public routes that behave differently for logged-in users.
 */
function optionalAuth(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (authHeader && authHeader.startsWith('Bearer ')) {
    try {
      req.user = jwt.verify(authHeader.split(' ')[1], JWT_SECRET);
    } catch {
      req.user = null;
    }
  }
  next();
}

module.exports = { requireAuth, optionalAuth };

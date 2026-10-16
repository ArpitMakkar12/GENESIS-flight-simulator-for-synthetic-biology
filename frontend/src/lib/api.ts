/*
 * Where the backend lives. Every page and component imports API from here,
 * so the address is set in exactly one place.
 *
 *   Local (Docker):  NEXT_PUBLIC_API_URL=http://localhost:8000   (docker-compose.yml)
 *   Online (Vercel): NEXT_PUBLIC_API_URL=https://<your-backend>.onrender.com
 *
 * NEXT_PUBLIC_ variables are written into the JavaScript when the frontend is
 * built, so after changing one on Vercel the site must be redeployed.
 */
const BACKEND = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");

export const API = `${BACKEND}/api/v1`;
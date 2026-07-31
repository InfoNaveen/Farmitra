/**
 * Farmitra API client
 *
 * In development the Vite proxy rewrites /api → http://localhost:8000
 * (configured in vite.config.js), so no CORS issues in dev.
 *
 * In production (Vercel) set VITE_API_URL to your backend URL, e.g.:
 *   VITE_API_URL=https://farmitra-backend.onrender.com
 *
 * The OpenAI key is NEVER exposed here — all AI calls go through the backend.
 */
import axios from 'axios'

// Use VITE_API_URL if set (production); fall back to /api proxy (dev)
const BASE_URL = import.meta.env.VITE_API_URL
  ? import.meta.env.VITE_API_URL.replace(/\/$/, '')   // strip trailing slash
  : '/api'

const http = axios.create({ baseURL: BASE_URL })

/** Health check */
export const checkHealth = () => http.get('/health')

/**
 * POST /diagnose — upload image, get disease label + confidence
 * @param {File} imageFile
 */
export const diagnoseImage = (imageFile) => {
  const form = new FormData()
  form.append('file', imageFile)
  return http.post('/diagnose', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

/**
 * POST /explain — get farmer-friendly chatbot explanation
 * @param {object} params
 * @param {string} params.disease_label
 * @param {number} params.confidence_score
 * @param {string} [params.crop_name]
 * @param {string} [params.user_question]
 */
export const explainDiagnosis = (params) => http.post('/explain', params)

/**
 * GET /price-trend?crop=<name>
 * @param {string} crop
 */
export const getPriceTrend = (crop) =>
  http.get('/price-trend', { params: { crop } })

/**
 * GET /weather?lat=<f>&lon=<f>
 * @param {number} lat
 * @param {number} lon
 */
export const getWeather = (lat = 20.5937, lon = 78.9629) =>
  http.get('/weather', { params: { lat, lon } })

/**
 * POST /advisor — sell/hold recommendation with tool-call trace
 * @param {string} crop
 * @param {string} [location]
 */
export const getAdvisorRecommendation = (crop, location = 'India') =>
  http.post('/advisor', { crop, location })

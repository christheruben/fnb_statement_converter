import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:5000',
  withCredentials: true, // sends httpOnly cookie with every request
})

export default api

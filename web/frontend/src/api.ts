import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api', // Адрес нашего FastAPI
});

export default api;
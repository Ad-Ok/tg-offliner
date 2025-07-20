import axios from 'axios';

export const apiBase =
  typeof window === 'undefined'
    ? 'http://app:5000'
    : 'http://localhost:5000';

export const api = axios.create({
  baseURL: apiBase,
});
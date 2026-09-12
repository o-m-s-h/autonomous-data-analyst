import axios from "axios";

export const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
});

export function errorMessage(error, fallback) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg || "Invalid input").join(". ");
    if (!error.response) return "We couldn't reach the analyst. Check that your backend is running, then try again.";
    return fallback;
}

import { useState, useEffect } from 'react';

export const useOllamaStatus = () => {
    const [isConnected, setIsConnected] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const checkStatus = async () => {
            try {
                // Assuming Ollama runs on port 11434 by default
                // In production, we might need a proxy or backend endpoint if CORS is an issue
                // For now, prompt the user if they're running it locally, or check via a fetch

                // Hack: Since we can't easily fetch localhost:11434 from browser due to CORS usually,
                // we might need to rely on our own backend proxy or just try fetch and catch error.
                // However, updated ComfyUI install might include Ollama.

                // Let's try a simple fetch to the default Ollama port
                const response = await fetch('/ollama/tags', {
                    method: 'GET',
                    // mode: 'no-cors' // opaque response, assumes it's up if no network error
                }).catch(() => null);

                if (response && response.ok) {
                    setIsConnected(true);
                } else {
                    setIsConnected(false);
                }
            } catch (error) {
                setIsConnected(false);
            } finally {
                setIsLoading(false);
            }
        };

        checkStatus();
        const interval = setInterval(checkStatus, 10000); // Check every 10s

        return () => clearInterval(interval);
    }, []);

    return { isConnected, isLoading };
};

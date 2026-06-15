export interface OllamaModel {
    name: string;
    size: number;
    digest: string;
    modified_at: string;
}

export interface OllamaProgress {
    status: string;
    digest?: string;
    total?: number;
    completed?: number;
}

export const ollamaService = {
    // List installed models
    getModels: async (): Promise<OllamaModel[]> => {
        try {
            const response = await fetch('/ollama/tags');
            if (!response.ok) throw new Error('Failed to fetch models');
            const data = await response.json();
            return data.models || [];
        } catch (error) {
            console.error('Ollama getModels error:', error);
            throw error;
        }
    },

    // Pull a new model
    pullModel: async (modelName: string, onProgress: (progress: OllamaProgress) => void) => {
        try {
            const response = await fetch('/ollama/pull', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: modelName, stream: true }),
            });

            if (!response.ok) throw new Error('Failed to pull model');
            if (!response.body) throw new Error('No response body');

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                // Ollama can send multiple JSON objects in one chunk
                const lines = chunk.split('\n').filter(line => line.trim() !== '');

                for (const line of lines) {
                    try {
                        const json = JSON.parse(line);
                        onProgress(json);
                    } catch (e) {
                        console.warn('Failed to parse Ollama status line:', line);
                    }
                }
            }
        } catch (error) {
            console.error('Ollama pull error:', error);
            throw error;
        }
    },

    // Delete a model
    deleteModel: async (modelName: string) => {
        try {
            const response = await fetch('/ollama/delete', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: modelName }),
            });
            if (!response.ok) throw new Error('Failed to delete model');
            return true;
        } catch (error) {
            console.error('Ollama delete error:', error);
            throw error;
        }
    },

    // Generate text using Ollama (non-streaming)
    generate: async (model: string, prompt: string, system?: string): Promise<string> => {
        try {
            const response = await fetch('/ollama/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model,
                    prompt,
                    system,
                    stream: false,
                    options: { temperature: 0.7, num_predict: 512 }
                }),
            });
            if (!response.ok) throw new Error('Ollama generate failed');
            const data = await response.json();
            return data.response?.trim() || '';
        } catch (error) {
            console.error('Ollama generate error:', error);
            throw error;
        }
    },

    // Unload model from VRAM (free memory for ComfyUI)
    unloadModel: async (modelName: string) => {
        try {
            console.log(`🧹 Unloading ${modelName} from VRAM...`);
            const response = await fetch('/ollama/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: modelName,
                    keep_alive: 0  // Immediately unload
                }),
            });
            if (!response.ok) {
                console.warn('Failed to unload model (non-critical)');
            } else {
                console.log('✅ Model unloaded from VRAM');
            }
        } catch (error) {
            console.warn('Ollama unload error (non-critical):', error);
        }
    }
};

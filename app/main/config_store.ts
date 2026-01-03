import Store from 'electron-store';

interface UserSettings {
    apiKey?: string;
    apiBaseUrl?: string; // For compatible APIs like DeepSeek
    modelName?: string;
    userName?: string;
    aiName?: string;
}

const schema = {
    apiKey: {
        type: 'string',
        default: '',
    },
    apiBaseUrl: {
        type: 'string',
        default: 'https://api.deepseek.com/v1', // Default to DeepSeek
    },
    modelName: {
        type: 'string',
        default: 'deepseek-chat',
    },
    userName: {
        type: 'string',
        default: 'User',
    },
    aiName: {
        type: 'string',
        default: 'Lumina',
    }
} as const;

const store = new Store<UserSettings>({ schema });

export default store;

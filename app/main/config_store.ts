import Store from 'electron-store';

interface UserSettings {
    activeCharacterId?: string;
    backgroundImage?: string;
    contextWindow?: number;
    isTTSEnabled?: boolean;
    live2d_high_dpi?: boolean;
    thinking_enabled?: boolean;
    userName?: string;
}

const schema = {
    activeCharacterId: {
        type: 'string',
        default: 'hiyori',
    },
    backgroundImage: {
        type: 'string',
        default: '',
    },
    contextWindow: {
        type: 'number',
        default: 50,
    },
    isTTSEnabled: {
        type: 'boolean',
        default: true,
    },
    live2d_high_dpi: {
        type: 'boolean',
        default: false,
    },
    thinking_enabled: {
        type: 'boolean',
        default: false,
    },
    userName: {
        type: 'string',
        default: 'Master',
    }
} as const;

const store = new Store<UserSettings>({ schema });

export default store;

import Store from 'electron-store';

interface UserSettings {
    backgroundImage?: string;
    contextWindow?: number;
    isTTSEnabled?: boolean;
    live2d_high_dpi?: boolean;
    live2d_view_state?: Record<string, unknown>;
    thinking_enabled?: boolean;
    userName?: string;
}

const schema = {
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
    live2d_view_state: {
        type: 'object',
        default: {},
        additionalProperties: {
            type: 'object',
        },
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

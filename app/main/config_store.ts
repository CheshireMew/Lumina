import Store from 'electron-store';
import { DEFAULT_USER_NAME } from '../shared/productDefaults';

interface UserSettings {
    backgroundImage?: string;
    isTTSEnabled?: boolean;
    live2d_high_dpi?: boolean;
    live2d_view_state?: Record<string, unknown>;
    userName?: string;
}

const schema = {
    backgroundImage: {
        type: 'string',
        default: '',
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
    userName: {
        type: 'string',
        default: DEFAULT_USER_NAME,
    }
} as const;

const store = new Store<UserSettings>({ schema });

export default store;

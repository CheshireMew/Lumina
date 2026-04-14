export interface AvatarModel {
    name: string;
    path: string;
    type?: "live2d" | "vrm" | "sprite";
    thumbnail?: string;
    availability?: "ready" | "installable";
}

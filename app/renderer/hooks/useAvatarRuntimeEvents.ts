import { useEffect } from "react";
import { events } from "../core/events";
import type { AvatarRendererRef, FaceTrackingData } from "../core/avatar/types";

export function useAvatarRuntimeEvents(
    avatarRef: React.RefObject<AvatarRendererRef>,
    interrupt: () => void,
) {
    useEffect(() => {
        const applyFaceData = (data: FaceTrackingData) => {
            avatarRef.current?.setBlendShapes?.(data);
        };
        const stopForInput = () => interrupt();

        const subscriptions = [
            events.on("audio:vad.start", stopForInput),
            events.on("core:interrupt", stopForInput),
            events.on("avatar:face_tracking", applyFaceData),
        ];
        return () => subscriptions.forEach((unsubscribe) => unsubscribe());
    }, [avatarRef, interrupt]);
}

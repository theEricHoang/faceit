import { create } from 'zustand';

interface AttendancePhotoStore {
  photos: string[];
  addPhoto: (uri: string) => void;
  removePhoto: (uri: string) => void;
  clearPhotos: () => void;
}

export const useAttendancePhotoStore = create<AttendancePhotoStore>((set) => ({
  photos: [],

  addPhoto: (uri: string) => {
    set((state) => ({ photos: [...state.photos, uri] }));
  },

  removePhoto: (uri: string) => {
    set((state) => ({ photos: state.photos.filter((p) => p !== uri) }));
  },

  clearPhotos: () => {
    set({ photos: [] });
  },
}));

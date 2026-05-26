import { configureStore } from '@reduxjs/toolkit';

// Placeholder slices - to be implemented
const placeholderReducer = (state = {}, action: any) => state;

export const store = configureStore({
  reducer: {
    auth: placeholderReducer,
    destinations: placeholderReducer,
    user: placeholderReducer,
    chat: placeholderReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
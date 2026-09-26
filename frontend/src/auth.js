import { createContext, useContext } from 'react'

/** Whether this copy of the app is protected by a password (a published website), and a way to sign out. */
export const AuthContext = createContext({ required: false, signOut: () => {} })

export const useAuth = () => useContext(AuthContext)

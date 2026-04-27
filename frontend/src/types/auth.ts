// Authentication types for the Evidence Seeker Platform

import { Permission } from "./permission";

export interface User {
  id: number;
  email: string;
  username: string;
  isActive: boolean;
  isSuperuser: boolean;
  isVerified: boolean;
  createdAt?: string;
  updatedAt?: string;
  permissions?: Permission[];
}

export interface UserCreate {
  email: string;
  password: string;
  isActive?: boolean;
  isSuperuser?: boolean;
  isVerified?: boolean;
}

export interface UserUpdate {
  email?: string;
  password?: string;
  isActive?: boolean;
  isSuperuser?: boolean;
  isVerified?: boolean;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export type RegisterErrorField = "email" | "username" | "password" | "form";

export interface RegisterError {
  field: RegisterErrorField;
  message: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  token_type: string;
  message: string;
}

export interface TokenData {
  access_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginFormData {
  email: string;
  password: string;
}

export interface RegisterFormData {
  email: string;
  username: string;
  password: string;
  confirmPassword: string;
}

export interface ApiError {
  detail: string;
  message?: string;
}

export interface User {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  imageUrl?: string;
  createdAt: string;
  updatedAt?: string;
}

export type UserRole = "admin" | "member" | "viewer";

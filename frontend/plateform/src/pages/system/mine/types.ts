import type { UserInfo } from "@/apis/system/data-contracts";

export type UserData = UserInfo;

export interface EditProfileFormData {
  userRealname: string;
  userEmail: string;
  userPhone: string;
}

export interface ResetPasswordFormData {
  oldPassword: string;
  newPassword: string;
  confirmPassword: string;
}

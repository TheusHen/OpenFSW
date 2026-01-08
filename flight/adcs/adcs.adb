--  OpenFSW ADCS Package Body
--  Implementation of attitude math and control algorithms

with Ada.Numerics.Elementary_Functions;

package body ADCS is
   
   use Ada.Numerics.Elementary_Functions;
   
   ---------------------------------------------------------------------------
   --  Quaternion Operations
   ---------------------------------------------------------------------------
   
   function Quaternion_Multiply (Q1, Q2 : Quaternion) return Quaternion is
   begin
      return (
         W => Q1.W * Q2.W - Q1.X * Q2.X - Q1.Y * Q2.Y - Q1.Z * Q2.Z,
         X => Q1.W * Q2.X + Q1.X * Q2.W + Q1.Y * Q2.Z - Q1.Z * Q2.Y,
         Y => Q1.W * Q2.Y - Q1.X * Q2.Z + Q1.Y * Q2.W + Q1.Z * Q2.X,
         Z => Q1.W * Q2.Z + Q1.X * Q2.Y - Q1.Y * Q2.X + Q1.Z * Q2.W
      );
   end Quaternion_Multiply;
   
   function Quaternion_Conjugate (Q : Quaternion) return Quaternion is
   begin
      return (W => Q.W, X => -Q.X, Y => -Q.Y, Z => -Q.Z);
   end Quaternion_Conjugate;
   
   function Quaternion_Normalize (Q : Quaternion) return Quaternion is
      Norm : constant Float32 := Sqrt (Float32 (
         Q.W * Q.W + Q.X * Q.X + Q.Y * Q.Y + Q.Z * Q.Z));
      Inv_Norm : Float32;
   begin
      if Norm < 1.0e-10 then
         return (W => 1.0, X => 0.0, Y => 0.0, Z => 0.0);
      end if;
      
      Inv_Norm := 1.0 / Norm;
      return (
         W => Q.W * Inv_Norm,
         X => Q.X * Inv_Norm,
         Y => Q.Y * Inv_Norm,
         Z => Q.Z * Inv_Norm
      );
   end Quaternion_Normalize;
   
   function Quaternion_To_DCM (Q : Quaternion) return Matrix3x3 is
      QW : constant Float32 := Q.W;
      QX : constant Float32 := Q.X;
      QY : constant Float32 := Q.Y;
      QZ : constant Float32 := Q.Z;
      
      QW2 : constant Float32 := QW * QW;
      QX2 : constant Float32 := QX * QX;
      QY2 : constant Float32 := QY * QY;
      QZ2 : constant Float32 := QZ * QZ;
   begin
      return (
         (QW2 + QX2 - QY2 - QZ2, 2.0 * (QX * QY - QW * QZ), 2.0 * (QX * QZ + QW * QY)),
         (2.0 * (QX * QY + QW * QZ), QW2 - QX2 + QY2 - QZ2, 2.0 * (QY * QZ - QW * QX)),
         (2.0 * (QX * QZ - QW * QY), 2.0 * (QY * QZ + QW * QX), QW2 - QX2 - QY2 + QZ2)
      );
   end Quaternion_To_DCM;
   
   ---------------------------------------------------------------------------
   --  Vector Operations
   ---------------------------------------------------------------------------
   
   function Vector_Add (A, B : Vector3) return Vector3 is
   begin
      return (X => A.X + B.X, Y => A.Y + B.Y, Z => A.Z + B.Z);
   end Vector_Add;
   
   function Vector_Subtract (A, B : Vector3) return Vector3 is
   begin
      return (X => A.X - B.X, Y => A.Y - B.Y, Z => A.Z - B.Z);
   end Vector_Subtract;
   
   function Vector_Scale (V : Vector3; S : Float32) return Vector3 is
   begin
      return (X => V.X * S, Y => V.Y * S, Z => V.Z * S);
   end Vector_Scale;
   
   function Vector_Cross (A, B : Vector3) return Vector3 is
   begin
      return (
         X => A.Y * B.Z - A.Z * B.Y,
         Y => A.Z * B.X - A.X * B.Z,
         Z => A.X * B.Y - A.Y * B.X
      );
   end Vector_Cross;
   
   function Vector_Dot (A, B : Vector3) return Float32 is
   begin
      return A.X * B.X + A.Y * B.Y + A.Z * B.Z;
   end Vector_Dot;
   
   function Vector_Norm (V : Vector3) return Float32 is
   begin
      return Sqrt (Float32 (V.X * V.X + V.Y * V.Y + V.Z * V.Z));
   end Vector_Norm;
   
   function Vector_Normalize (V : Vector3) return Vector3 is
      Norm : constant Float32 := Vector_Norm (V);
   begin
      if Norm < 1.0e-10 then
         return (X => 0.0, Y => 0.0, Z => 0.0);
      end if;
      return Vector_Scale (V, 1.0 / Norm);
   end Vector_Normalize;
   
   ---------------------------------------------------------------------------
   --  Matrix Operations
   ---------------------------------------------------------------------------
   
   function Matrix_Vector_Multiply (M : Matrix3x3; V : Vector3) return Vector3 is
   begin
      return (
         X => M (1, 1) * V.X + M (1, 2) * V.Y + M (1, 3) * V.Z,
         Y => M (2, 1) * V.X + M (2, 2) * V.Y + M (2, 3) * V.Z,
         Z => M (3, 1) * V.X + M (3, 2) * V.Y + M (3, 3) * V.Z
      );
   end Matrix_Vector_Multiply;
   
end ADCS;

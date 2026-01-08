--  OpenFSW ADCS Package Specification
--  Attitude Determination and Control System
--  
--  Critical control in Ada for safety

with Interfaces; use Interfaces;

package ADCS is
   pragma Pure;
   
   ---------------------------------------------------------------------------
   --  Types
   ---------------------------------------------------------------------------
   
   type Float32 is new Interfaces.IEEE_Float_32;
   type Float64 is new Interfaces.IEEE_Float_64;
   
   --  3D Vector
   type Vector3 is record
      X : Float32;
      Y : Float32;
      Z : Float32;
   end record;
   
   --  Quaternion (scalar-first: w, x, y, z)
   type Quaternion is record
      W : Float32;
      X : Float32;
      Y : Float32;
      Z : Float32;
   end record;
   
   --  3x3 Matrix (row-major)
   type Matrix3x3 is array (1 .. 3, 1 .. 3) of Float32;
   
   --  ADCS Mode
   type ADCS_Mode is (
      ADCS_Off,
      ADCS_Safe,
      ADCS_Detumble,
      ADCS_Sun_Point,
      ADCS_Nadir_Point,
      ADCS_Target_Track
   );
   
   --  Sensor Status
   type Sensor_Status is (
      Sensor_OK,
      Sensor_Degraded,
      Sensor_Failed,
      Sensor_Not_Available
   );
   
   --  Magnetometer Reading
   type Magnetometer_Data is record
      Field     : Vector3;  --  Magnetic field in body frame (uT)
      Status    : Sensor_Status;
      Timestamp : Unsigned_32;
   end record;
   
   --  Gyroscope Reading
   type Gyroscope_Data is record
      Rate      : Vector3;  --  Angular rate in body frame (rad/s)
      Status    : Sensor_Status;
      Timestamp : Unsigned_32;
   end record;
   
   --  Sun Sensor Reading
   type Sun_Sensor_Data is record
      Direction : Vector3;  --  Sun direction in body frame (unit vector)
      Valid     : Boolean;  --  True if sun is visible
      Status    : Sensor_Status;
      Timestamp : Unsigned_32;
   end record;
   
   --  Attitude State
   type Attitude_State is record
      Quaternion_Est : Quaternion;
      Angular_Rate   : Vector3;
      Attitude_Valid : Boolean;
      Rate_Valid     : Boolean;
   end record;
   
   --  Control Output
   type Control_Output is record
      Torque_Cmd  : Vector3;  --  Commanded torque (Nm)
      Dipole_Cmd  : Vector3;  --  Magnetorquer dipole command (Am²)
      Valid       : Boolean;
   end record;
   
   --  ADCS Telemetry
   type ADCS_Telemetry is record
      Mode          : ADCS_Mode;
      Attitude      : Attitude_State;
      Control       : Control_Output;
      Mag_Data      : Magnetometer_Data;
      Gyro_Data     : Gyroscope_Data;
      Sun_Data      : Sun_Sensor_Data;
      Control_Error : Float32;  --  Attitude error magnitude (rad)
   end record;
   
   ---------------------------------------------------------------------------
   --  Constants
   ---------------------------------------------------------------------------
   
   --  Control gains
   Detumble_Gain : constant Float32 := 1.0e-5;
   Pointing_Kp   : constant Float32 := 0.01;
   Pointing_Kd   : constant Float32 := 0.1;
   
   --  Thresholds
   Detumble_Rate_Threshold : constant Float32 := 0.02;  --  rad/s
   Pointing_Error_Threshold : constant Float32 := 0.087;  --  5 degrees
   
   --  Actuator limits
   Max_Dipole : constant Float32 := 0.2;  --  Am²
   
   ---------------------------------------------------------------------------
   --  Operations
   ---------------------------------------------------------------------------
   
   --  Quaternion operations
   function Quaternion_Multiply (Q1, Q2 : Quaternion) return Quaternion;
   function Quaternion_Conjugate (Q : Quaternion) return Quaternion;
   function Quaternion_Normalize (Q : Quaternion) return Quaternion;
   function Quaternion_To_DCM (Q : Quaternion) return Matrix3x3;
   
   --  Vector operations
   function Vector_Add (A, B : Vector3) return Vector3;
   function Vector_Subtract (A, B : Vector3) return Vector3;
   function Vector_Scale (V : Vector3; S : Float32) return Vector3;
   function Vector_Cross (A, B : Vector3) return Vector3;
   function Vector_Dot (A, B : Vector3) return Float32;
   function Vector_Norm (V : Vector3) return Float32;
   function Vector_Normalize (V : Vector3) return Vector3;
   
   --  Matrix operations
   function Matrix_Vector_Multiply (M : Matrix3x3; V : Vector3) return Vector3;
   
end ADCS;

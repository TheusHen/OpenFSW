--  OpenFSW ADCS Controller Package Specification
--  Control algorithms for attitude control

package ADCS.Controller is
   
   ---------------------------------------------------------------------------
   --  Controller State
   ---------------------------------------------------------------------------
   
   type Controller_State is record
      Mode              : ADCS_Mode;
      Target_Quaternion : Quaternion;
      Error_Quaternion  : Quaternion;
      Error_Angle       : Float32;
      Integral_Error    : Vector3;
      Last_Rate_Error   : Vector3;
      Initialized       : Boolean;
   end record;
   
   ---------------------------------------------------------------------------
   --  Procedures
   ---------------------------------------------------------------------------
   
   --  Initialize controller
   procedure Initialize (State : out Controller_State);
   
   --  Set operating mode
   procedure Set_Mode (State : in out Controller_State; Mode : ADCS_Mode);
   
   --  Set target attitude
   procedure Set_Target (State : in out Controller_State; Target : Quaternion);
   
   --  B-dot detumbling controller
   --  Uses magnetic field derivative to reduce angular rate
   procedure Detumble_Controller (
      Mag_Current  : Vector3;
      Mag_Previous : Vector3;
      Dt           : Float32;
      Dipole_Cmd   : out Vector3;
      Valid        : out Boolean
   );
   
   --  Nadir pointing controller
   --  Points +Z axis toward Earth
   procedure Nadir_Controller (
      State       : in out Controller_State;
      Current_Att : Attitude_State;
      Mag_Field   : Vector3;
      Dipole_Cmd  : out Vector3;
      Valid       : out Boolean
   );
   
   --  Sun pointing controller
   --  Points solar panels toward sun
   procedure Sun_Point_Controller (
      State       : in Out Controller_State;
      Current_Att : Attitude_State;
      Sun_Dir     : Vector3;
      Mag_Field   : Vector3;
      Dipole_Cmd  : out Vector3;
      Valid       : out Boolean
   );
   
   --  Main control step
   procedure Control_Step (
      State       : in out Controller_State;
      Attitude    : Attitude_State;
      Mag_Data    : Magnetometer_Data;
      Mag_Prev    : Magnetometer_Data;
      Sun_Data    : Sun_Sensor_Data;
      Dt          : Float32;
      Output      : out Control_Output
   );
   
   --  Check if detumble complete
   function Is_Detumbled (Rate : Vector3) return Boolean;
   
   --  Get attitude error angle
   function Get_Error_Angle (State : Controller_State) return Float32;
   
end ADCS.Controller;

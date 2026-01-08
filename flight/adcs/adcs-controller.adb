--  OpenFSW ADCS Controller Package Body

package body ADCS.Controller is
   
   ---------------------------------------------------------------------------
   --  Initialization
   ---------------------------------------------------------------------------
   
   procedure Initialize (State : out Controller_State) is
   begin
      State.Mode := ADCS_Off;
      State.Target_Quaternion := (W => 1.0, X => 0.0, Y => 0.0, Z => 0.0);
      State.Error_Quaternion := (W => 1.0, X => 0.0, Y => 0.0, Z => 0.0);
      State.Error_Angle := 0.0;
      State.Integral_Error := (X => 0.0, Y => 0.0, Z => 0.0);
      State.Last_Rate_Error := (X => 0.0, Y => 0.0, Z => 0.0);
      State.Initialized := True;
   end Initialize;
   
   procedure Set_Mode (State : in out Controller_State; Mode : ADCS_Mode) is
   begin
      State.Mode := Mode;
      --  Reset integral on mode change
      State.Integral_Error := (X => 0.0, Y => 0.0, Z => 0.0);
   end Set_Mode;
   
   procedure Set_Target (State : in Out Controller_State; Target : Quaternion) is
   begin
      State.Target_Quaternion := Quaternion_Normalize (Target);
   end Set_Target;
   
   ---------------------------------------------------------------------------
   --  B-Dot Detumbling Controller
   ---------------------------------------------------------------------------
   
   procedure Detumble_Controller (
      Mag_Current  : Vector3;
      Mag_Previous : Vector3;
      Dt           : Float32;
      Dipole_Cmd   : out Vector3;
      Valid        : out Boolean
   ) is
      B_Dot : Vector3;
      Dipole : Vector3;
      Dipole_Norm : Float32;
   begin
      Valid := False;
      Dipole_Cmd := (X => 0.0, Y => 0.0, Z => 0.0);
      
      if Dt < 1.0e-6 then
         return;
      end if;
      
      --  Compute magnetic field derivative (B-dot)
      B_Dot := Vector_Scale (
         Vector_Subtract (Mag_Current, Mag_Previous),
         1.0 / Dt
      );
      
      --  B-dot control law: m = -k * B_dot
      Dipole := Vector_Scale (B_Dot, -Detumble_Gain);
      
      --  Limit dipole magnitude
      Dipole_Norm := Vector_Norm (Dipole);
      if Dipole_Norm > Max_Dipole then
         Dipole := Vector_Scale (Dipole, Max_Dipole / Dipole_Norm);
      end if;
      
      Dipole_Cmd := Dipole;
      Valid := True;
   end Detumble_Controller;
   
   ---------------------------------------------------------------------------
   --  Nadir Pointing Controller
   ---------------------------------------------------------------------------
   
   procedure Nadir_Controller (
      State       : in Out Controller_State;
      Current_Att : Attitude_State;
      Mag_Field   : Vector3;
      Dipole_Cmd  : out Vector3;
      Valid       : out Boolean
   ) is
      Error_Vec : Vector3;
      Rate_Error : Vector3;
      Torque_Cmd : Vector3;
      Dipole : Vector3;
      B_Norm : Float32;
   begin
      Valid := False;
      Dipole_Cmd := (X => 0.0, Y => 0.0, Z => 0.0);
      
      if not Current_Att.Attitude_Valid then
         return;
      end if;
      
      --  Compute quaternion error
      State.Error_Quaternion := Quaternion_Multiply (
         Quaternion_Conjugate (Current_Att.Quaternion_Est),
         State.Target_Quaternion
      );
      
      --  Ensure short rotation path
      if State.Error_Quaternion.W < 0.0 then
         State.Error_Quaternion := (
            W => -State.Error_Quaternion.W,
            X => -State.Error_Quaternion.X,
            Y => -State.Error_Quaternion.Y,
            Z => -State.Error_Quaternion.Z
         );
      end if;
      
      --  Error vector (proportional term)
      Error_Vec := (
         X => State.Error_Quaternion.X,
         Y => State.Error_Quaternion.Y,
         Z => State.Error_Quaternion.Z
      );
      Error_Vec := Vector_Scale (Error_Vec, 2.0 * Pointing_Kp);
      
      --  Rate error (derivative term)
      Rate_Error := Vector_Scale (Current_Att.Angular_Rate, -Pointing_Kd);
      
      --  Total torque command
      Torque_Cmd := Vector_Add (Error_Vec, Rate_Error);
      
      --  Convert torque to dipole using cross product with B field
      --  T = m x B  =>  m = (B x T) / |B|²
      B_Norm := Vector_Norm (Mag_Field);
      if B_Norm < 1.0e-6 then
         return;
      end if;
      
      Dipole := Vector_Cross (Mag_Field, Torque_Cmd);
      Dipole := Vector_Scale (Dipole, 1.0 / (B_Norm * B_Norm));
      
      --  Limit dipole magnitude
      declare
         Dipole_Norm : constant Float32 := Vector_Norm (Dipole);
      begin
         if Dipole_Norm > Max_Dipole then
            Dipole := Vector_Scale (Dipole, Max_Dipole / Dipole_Norm);
         end if;
      end;
      
      --  Compute error angle for telemetry
      State.Error_Angle := 2.0 * Arcsin (Float32 (Vector_Norm ((
         X => State.Error_Quaternion.X,
         Y => State.Error_Quaternion.Y,
         Z => State.Error_Quaternion.Z
      ))));
      
      Dipole_Cmd := Dipole;
      Valid := True;
   end Nadir_Controller;
   
   ---------------------------------------------------------------------------
   --  Sun Pointing Controller
   ---------------------------------------------------------------------------
   
   procedure Sun_Point_Controller (
      State       : in Out Controller_State;
      Current_Att : Attitude_State;
      Sun_Dir     : Vector3;
      Mag_Field   : Vector3;
      Dipole_Cmd  : out Vector3;
      Valid       : out Boolean
   ) is
      --  Target: align +X axis with sun direction
      Target_X : constant Vector3 := Vector_Normalize (Sun_Dir);
      Error_Vec : Vector3;
      Torque_Cmd : Vector3;
      Dipole : Vector3;
      B_Norm : Float32;
   begin
      Valid := False;
      Dipole_Cmd := (X => 0.0, Y => 0.0, Z => 0.0);
      
      if Vector_Norm (Sun_Dir) < 0.1 then
         --  Sun not visible, use safe mode behavior
         return;
      end if;
      
      --  Error is cross product between current X axis and target
      --  For now, assume body X axis is (1, 0, 0) in body frame
      Error_Vec := Vector_Cross ((X => 1.0, Y => 0.0, Z => 0.0), Target_X);
      Error_Vec := Vector_Scale (Error_Vec, Pointing_Kp);
      
      --  Add rate damping
      Torque_Cmd := Vector_Subtract (
         Error_Vec,
         Vector_Scale (Current_Att.Angular_Rate, Pointing_Kd)
      );
      
      --  Convert to dipole
      B_Norm := Vector_Norm (Mag_Field);
      if B_Norm < 1.0e-6 then
         return;
      end if;
      
      Dipole := Vector_Cross (Mag_Field, Torque_Cmd);
      Dipole := Vector_Scale (Dipole, 1.0 / (B_Norm * B_Norm));
      
      --  Limit
      declare
         Dipole_Norm : constant Float32 := Vector_Norm (Dipole);
      begin
         if Dipole_Norm > Max_Dipole then
            Dipole := Vector_Scale (Dipole, Max_Dipole / Dipole_Norm);
         end if;
      end;
      
      State.Error_Angle := Arccos (Float32 (Vector_Dot (
         (X => 1.0, Y => 0.0, Z => 0.0),
         Target_X
      )));
      
      Dipole_Cmd := Dipole;
      Valid := True;
   end Sun_Point_Controller;
   
   ---------------------------------------------------------------------------
   --  Main Control Step
   ---------------------------------------------------------------------------
   
   procedure Control_Step (
      State       : in Out Controller_State;
      Attitude    : Attitude_State;
      Mag_Data    : Magnetometer_Data;
      Mag_Prev    : Magnetometer_Data;
      Sun_Data    : Sun_Sensor_Data;
      Dt          : Float32;
      Output      : out Control_Output
   ) is
   begin
      Output.Torque_Cmd := (X => 0.0, Y => 0.0, Z => 0.0);
      Output.Dipole_Cmd := (X => 0.0, Y => 0.0, Z => 0.0);
      Output.Valid := False;
      
      if not State.Initialized then
         return;
      end if;
      
      case State.Mode is
         when ADCS_Off =>
            Output.Valid := True;
            
         when ADCS_Safe =>
            --  Safe mode: just detumble
            Detumble_Controller (
               Mag_Current  => Mag_Data.Field,
               Mag_Previous => Mag_Prev.Field,
               Dt           => Dt,
               Dipole_Cmd   => Output.Dipole_Cmd,
               Valid        => Output.Valid
            );
            
         when ADCS_Detumble =>
            Detumble_Controller (
               Mag_Current  => Mag_Data.Field,
               Mag_Previous => Mag_Prev.Field,
               Dt           => Dt,
               Dipole_Cmd   => Output.Dipole_Cmd,
               Valid        => Output.Valid
            );
            
         when ADCS_Sun_Point =>
            if Sun_Data.Valid then
               Sun_Point_Controller (
                  State       => State,
                  Current_Att => Attitude,
                  Sun_Dir     => Sun_Data.Direction,
                  Mag_Field   => Mag_Data.Field,
                  Dipole_Cmd  => Output.Dipole_Cmd,
                  Valid       => Output.Valid
               );
            else
               --  Fall back to detumble if sun not visible
               Detumble_Controller (
                  Mag_Current  => Mag_Data.Field,
                  Mag_Previous => Mag_Prev.Field,
                  Dt           => Dt,
                  Dipole_Cmd   => Output.Dipole_Cmd,
                  Valid        => Output.Valid
               );
            end if;
            
         when ADCS_Nadir_Point | ADCS_Target_Track =>
            Nadir_Controller (
               State       => State,
               Current_Att => Attitude,
               Mag_Field   => Mag_Data.Field,
               Dipole_Cmd  => Output.Dipole_Cmd,
               Valid       => Output.Valid
            );
      end case;
   end Control_Step;
   
   ---------------------------------------------------------------------------
   --  Utility Functions
   ---------------------------------------------------------------------------
   
   function Is_Detumbled (Rate : Vector3) return Boolean is
   begin
      return Vector_Norm (Rate) < Detumble_Rate_Threshold;
   end Is_Detumbled;
   
   function Get_Error_Angle (State : Controller_State) return Float32 is
   begin
      return State.Error_Angle;
   end Get_Error_Angle;
   
end ADCS.Controller;

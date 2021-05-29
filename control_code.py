from roboclaw_3 import Roboclaw
from time import sleep
import numpy as np
from threading import Thread
from optimizer import Optimizer

class Footballmachine:
    def __init__(self,address=[0x80,0x81],baudrate=38400,port="/dev/ttyS0"):
        self.address = address
        self.rc = Roboclaw(port, baudrate)
        self.rc.Open()
        self.M1speedconst=1.0
        self.M2speedconst=1.0
        self.optim=Optimizer()

    def has_angle_motor_stopped_moving(self):
        interval = 0.1
        first = self.rc.ReadEncM1(self.address[1])
        sleep(interval)
        second = self.rc.ReadEncM1(self.address[1])
        print(f"first: {first}, second: {second}")
        while(first!=second): 
            first = self.rc.ReadEncM1(self.address[1])
            sleep(interval)
            second = self.rc.ReadEncM1(self.address[1])

    def init_motors(self):
        for address in self.address:
            version = self.rc.ReadVersion(address)
            if version[0]==False:
                print(f"GETVERSION Failed - check power supply and conections on address {address}")
                #return
            else:
                print(repr(version[1]))

        print("Initializing all motors...")
        backward_speed = 126 #range: 0-126
        self.rc.BackwardM1(self.address[1],backward_speed)
        self.has_angle_motor_stopped_moving()
        self.rc.BackwardM1(self.address[1],0)
        self.rc.ResetEncoders(self.address[1])
        print("Angle encoder:", self.rc.ReadEncM1(self.address[1])[1])      

    def _displayspeed(self):
        enc1 = self.rc.ReadEncM1(self.address[0])
        enc2 = self.rc.ReadEncM2(self.address[0])
        speed1 = self.rc.ReadSpeedM1(self.address[0])
        speed2 = self.rc.ReadSpeedM2(self.address[0])

        print(("Encoder1:"), end=' ')
        if(enc1[0]==1):
            print(enc1[1], end=' ')
            print(format(enc1[2],'02x'), end=' ')
        else:
            print("failed", end=' ')
        print("Encoder2:", end=' ')
        if(enc2[0]==1):
            print(enc2[1], end=' ')
            print(format(enc2[2],'02x'), end=' ')
        else:
            print("failed ", end=' ')
        print("Speed1:", end=' ')
        if(speed1[0]):
            print(speed1[1], end=' ')
        else:
            print("failed", end=' ')
        print(("Speed2:"), end=' ')
        if(speed2[0]):
            print(speed2[1])
        else:
            print("failed ")

    def _physics_speed_to_QPPS(self,speed):
        radius = 0.1
        encoder_pulses_per_rad = 1024/2
        angular_speed=speed/(2*np.pi*radius)
        QPPS=encoder_pulses_per_rad*angular_speed
        return QPPS
        
    def _speed_to_QPPS(self,speed):
        angular_speed=speed/(0.1*2*3.14)
        QPPS=int(round(angular_speed*4000))
        return QPPS 

    def _QPPS_to_speed(self,QPPS):
        radius = 0.1
        encoder_pulses_per_rad = 1024/2
        angular_speed=QPPS/encoder_pulses_per_rad
        speed=angular_speed*(2*np.pi*radius)
        return speed

    def _angle_to_QP(self,angle):
        range_min=0
        range_max=221
        angle_min=0
        angle_max=45
        a1=int(angle) - angle_min
        a2=range_max - range_min
        a3=angle_max - angle_min
        angle = int((a1 *a2)/a3 + range_min)
        return angle

    def set_angle(self,angle):
        print("Set_angle: ",angle)
        angle = self._angle_to_QP(angle)
        print("Target position M1:", angle)
        self.rc.SpeedAccelDeccelPositionM1(self.address[1],10,10,10,angle,0)
        self.has_angle_motor_stopped_moving()
        print("Angle encoder:", self.rc.ReadEncM1(self.address[1])[1])

    def set_speed_then_stop(self,speed):
        print("Set_speed: ",speed)
        speed=self._speed_to_QPPS(int(speed))
        speedm2=int(speed*self.M2speedconst)
        speedm1=int(speed*self.M1speedconst)
        self.rc.SpeedAccelM2(self.address[0],22000,speedm2)
        self.rc.SpeedAccelM1(self.address[0],22000,speedm1)
        sleep(4)
        self.rc.SpeedAccelM2(self.address[0],22000,0)
        self.rc.SpeedAccelM1(self.address[0],22000,0)

    def set_speed(self,speed):
        print("Set_speed: ",speed)
        speed=self._speed_to_QPPS(int(speed))
        speedm2=int(speed*self.M2speedconst)
        speedm1=int(speed*self.M1speedconst)
        self.rc.SpeedAccelM2(self.address[0],14000,speedm1)
        self.rc.SpeedAccelM1(self.address[0],14000,speedm2)
        for i in range(0,50):
            print(("{} # ".format(i)), end=' ')
            self._displayspeed() 
            sleep(0.1)

    def set_dispenser_speed(self,speed):
        print("Setdsipenser_speed: ",speed)
        self.rc.ForwardM2(self.address[1],speed)

    def check_speed(self,seconds):
        for i in range(0,seconds):
            print(("{} # ".format(i)), end=' ')
            self._displayspeed() 
            sleep(0.1)

    def calibrate_motors_encoder(self,speed):
        speed=self._speed_to_QPPS(int(speed))
        self.rc.SpeedAccelM1(self.address[0],14000,int(speed))
        self.rc.SpeedAccelM2(self.address[0],14000,int(speed))
        minspeedM1= np.Inf
        minspeedM2= np.Inf
        print("Wait two seconds before sending the ball. Film and measure landing position")
        sleep(4.5)
        for i in range(0,100):
            speed1 = self.rc.ReadSpeedM1(self.address[0])
            speed2 = self.rc.ReadSpeedM2(self.address[0])
            if(speed1[0]):
                if speed1[1]<minspeedM1: minspeedM1= speed1[1]
            if(speed2[0]):
                if speed2[1]<minspeedM2: minspeedM2= speed2[1]
            sleep(0.1)
        self.rc.SpeedAccelM2(self.address[0],22000,0)
        self.rc.SpeedAccelM1(self.address[0],22000,0)
        if not (minspeedM1==0 or minspeedM2==0):
            self.M1speedconst=speed/minspeedM1
            self.M2speedconst=speed/minspeedM2
            print("M1const: ",self.M1speedconst) 
            print("M2const: ",self.M2speedconst) 
            print("minM1speed: ",minspeedM1)
            print("minM2speed: ",minspeedM2)
        else:
            print("Error: minspeed==0")
        return speed, self.M1speedconst,self.M2speedconst, minspeedM1, minspeedM2  
        

    def calibrate_motor_M1(self,setspeed,realspeed):
        self.M1speedconst=setspeed/realspeed
        return self.M1speedconst

    def calibrate_motor_M2(self,setspeed,realspeed):
        self.M2speedconst=setspeed/realspeed 
        return self.M2speedconst
        
    def check_lowest_speeds(self):
        minspeedM1= np.Inf
        minspeedM2= np.Inf
        print("Wait two seconds before sending the ball. Film and measure landing position")
        sleep(2)
        for i in range(0,100):
            speed1 = self.rc.ReadSpeedM1(self.address[0])
            speed2 = self.rc.ReadSpeedM2(self.address[0])
            if(speed1[0]):
                if speed1[1]<minspeedM1: minspeedM1= speed1[1]
            if(speed2[0]):
                if speed2[1]<minspeedM2: minspeedM2= speed2[1]
            sleep(0.1)
        return self._QPPS_to_speed(minspeedM1), self._QPPS_to_speed(minspeedM2)
    
    def _manuell_shot(self,speed,angle,dispenser_speed):
        
        print("Set_angle: ",angle)
        angle = self._angle_to_QP(angle)
        print("Target position M1:", angle)
        t0 = Thread(target=self.rc.SpeedAccelDeccelPositionM1,args=(self.address[1],10,10,10,angle,0))
        t0.start()
        t0.join()
        print("Angle encoder:", self.rc.ReadEncM1(self.address[1])[1])

        #spin er gitt i radianer per sekund

        speed=self._speed_to_QPPS(int(speed))
        speedm2=int(speed*self.M2speedconst)
        speedm1=int(speed*self.M1speedconst)
        t1 = Thread(target=self.rc.SpeedAccelM2,args=(self.address[0],14000,speedm1))
        t2 = Thread(target=self.rc.SpeedAccelM1,args=(self.address[0],14000,speedm2))
        t3 = Thread(target=self.rc.ForwardM2,args=(self.address[1],dispenser_speed))


        t1.start()
        t2.start()
        t1.join()
        t2.join() 
        t3.start()
        t3.join()

    def manuell_shot(self,speed,angle,dispenser_speed):
        
        print("Set_angle: ",angle)
        angle = self._angle_to_QP(angle)
        print("Target position M1:", angle)
        t0 = Thread(target=self.rc.SpeedAccelDeccelPositionM1,args=(self.address[1],10,10,10,angle,0))
        t0.start()
        t0.join()
        print("Angle encoder:", self.rc.ReadEncM1(self.address[1])[1])

        #spin er gitt i radianer per sekund

        speed=self._speed_to_QPPS(int(speed))
        speedm2=int(speed*self.M2speedconst)
        speedm1=int(speed*self.M1speedconst)
        self.rc.SpeedAccelM2(self.address[0],14000,speedm1)
        self.rc.SpeedAccelM1(self.address[0],14000,speedm2)
        self.rc.ForwardM2(self.address[1],dispenser_speed)


    def manuell_shot_done(self):

        self.rc.SpeedAccelM2(self.address[0],14000,0)
        self.rc.SpeedAccelM1(self.address[0],14000,0)
        self.rc.ForwardM2(self.address[1],0)

        t0 = Thread(target=self.rc.SpeedAccelDeccelPositionM1,args=(self.address[1],10,10,10,0,0))
        t0.start()
        t0.join()

    def landing_shot(self,target,dispenser_speed):
        
        speed,angle,spin,tf= self.optim.find_initvalues_spin(target)
        #self.optim.plot_path(speed,angle,spin)
        print(f"Optim values for {target} is {speed,angle,spin}")
        print("Set_angle: ",angle)
        angle = self._angle_to_QP(angle)
        print("Target position M1:", angle)
        #self.rc.SpeedAccelDeccelPositionM1(self.address[1],10,10,10,angle,0)
        t0 = Thread(target=self.rc.SpeedAccelDeccelPositionM1,args=(self.address[1],10,10,10,angle,0))
        t0.start()
        t0.join()
        print("Angle encoder:", self.rc.ReadEncM1(self.address[1])[1])

        #spin er gitt i radianer per sekund
        sleep(7)
        speed=self._speed_to_QPPS(int(speed))
        speedm2=int(speed*self.M2speedconst)
        speedm1=int(speed*self.M1speedconst)
        self.rc.SpeedAccelM2(self.address[0],14000,speedm1)
        self.rc.SpeedAccelM1(self.address[0],14000,speedm2)
        self.rc.ForwardM2(self.address[1],dispenser_speed)
        return speed,angle,spin

    def manuell_shot_done(self):

        self.rc.SpeedAccelM2(self.address[0],14000,0)
        self.rc.SpeedAccelM1(self.address[0],14000,0)
        self.rc.ForwardM2(self.address[1],0)

        t0 = Thread(target=self.rc.SpeedAccelDeccelPositionM1,args=(self.address[1],10,10,10,0,0))
        t0.start()
        t0.join()


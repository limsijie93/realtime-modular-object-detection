import cv2
import time
import numpy as np
import csv
from display import Display
from predict import Predictor

from imutils.video import FileVideoStream
from imutils.video import FPS
import imutils

class Detection():
    def __init__(self, w, h):
        self.cheat_data = self.read_csv('../detector/data/data.csv')
        
        self.obj_name = 'person'
        self.c_start = 0
        self.prev_imgs = []

        self.resize_w = w
        self.resize_h = h
        self.multi = w/1920

        self.p = Predictor(self.resize_w, self.resize_h, 'models/model_detectorv2.h5')

        self.of_w = 376
        self.of_h = 240
        self.skipped_frames = 3

        self.rect_color = (10,125,10)
        self.font_size = 1
        self.font_thickness = 1

    def calc_of(self, pimg, cimg):
        p_resize = cv2.resize(pimg, (self.of_w, self.of_h))
        c_resize = cv2.resize(cimg, (self.of_w, self.of_h))
        pimg_gray = cv2.cvtColor(p_resize, cv2.COLOR_BGR2GRAY)
        cimg_gray = cv2.cvtColor(c_resize, cv2.COLOR_BGR2GRAY)
    

        hsv = np.zeros_like(p_resize)
    
        flow = cv2.calcOpticalFlowFarneback(pimg_gray, cimg_gray, None, 0.75, 3, 25, 3, 7, 1.2, 0)
    
        mag, ang = cv2.cartToPolar(flow[...,0], flow[...,1])
        hsv[...,2] = cv2.normalize(mag,None,0,255,cv2.NORM_MINMAX)
        bgr = cv2.cvtColor(hsv,cv2.COLOR_HSV2BGR)
        ret,bgr = cv2.threshold(hsv[...,2],10,255,cv2.THRESH_BINARY)
        bgr = cv2.resize(bgr, (self.resize_w, self.resize_h))
        return bgr

    def cheat_detect(self, img, nframe):
        clone = img.copy()
       
        flow = []
        if len(self.prev_imgs) == self.skipped_frames:
            flow = self.calc_of(self.prev_imgs[0], img)
        self.prev_imgs.append(img) 

        for i in range(self.c_start, len(self.cheat_data)):
            label = self.cheat_data[i]
            if label[1] > nframe:
                self.c_start = i
                break

            #find cleaner way to instantiate this
            rect = [(int(label[8]*self.multi) if label[8] > 0 else 0, 
                    int(label[9]*self.multi) if label[9] > 0 else 0), 
                    (int(label[10]*self.multi) if label[10] > 0 else 0, 
                    int(label[11]*self.multi) if label[11] > 0 else 0)]
           
            moving, color = self.is_moving(flow, rect, type='color')

            cv2.rectangle(clone, rect[0], rect[1], color, 2) 
            self.prev_img = img
        return clone        

    def detect_nn(self, img):
        mask_image = cv2.resize(self.p.detect_object(img), (self.resize_w, self.resize_h))
        _, contours, heir = cv2.findContours(mask_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detection = img.copy()

        flow = []
        if len(self.prev_imgs) == self.skipped_frames:
            flow = self.calc_of(self.prev_imgs[0], img)
            del self.prev_imgs[0]
        self.prev_imgs.append(img)

        for i in contours:
            if cv2.contourArea(i) < 500:
                continue
            (x,y,w,h) = cv2.boundingRect(i)
            rect = [(x,y),(x+w,y+h)]
            moving, color = self.is_moving(flow, rect, type='color')

            cv2.rectangle(detection, rect[0], rect[1], color,2)

            moving_label = 'n/a'
            if moving==1:
                moving_label = 'moving'
            elif moving==0:
                moving_label = 'not moving'

            label = '{}: {}'.format(self.obj_name, moving_label)
            (retval,baseLine) = cv2.getTextSize(label,cv2.FONT_HERSHEY_DUPLEX,self.font_size,self.font_thickness)
            textPos = (x,y)

            cv2.rectangle(detection, (textPos[0]-5, textPos[1]+baseLine-5), (textPos[0]+retval[0]+5, textPos[1]-retval[1]-5), (0,0,0), 2)
            cv2.rectangle(detection, (textPos[0]-5, textPos[1]+baseLine-5), (textPos[0]+retval[0]+5, textPos[1]-retval[1]-5), (255,255,255), -1)
            cv2.putText(detection, label, textPos, cv2.FONT_HERSHEY_DUPLEX, self.font_size, (0,0,0), self.font_thickness)
  

        return detection

    #HAS ISSUES WHEN PERSON IS BEHIND AN OBSTACLE
    #fix: be able to have a mask around the pedestrain and not a bounding box
    def is_moving(self, flow, rect,  type='none'):
        if len(flow) == 0:
            #can't tell
            if type=='color':
                return -1, (self.rect_color[0]*2, self.rect_color[1], self.rect_color[2])
            return -1

        flow_crop = flow[rect[0][1]:rect[1][1], rect[0][0]:rect[1][0]]
        white_count = cv2.countNonZero(flow_crop)

        flow_per = white_count/(flow_crop.shape[0]*flow_crop.shape[1])

        if flow_per > 0.2:
            #moving
            if type=='color':
                return 1, (self.rect_color[0], self.rect_color[1]*2, self.rect_color[2])
            return 1
        #not moving
        if type =='color':
            return 0, (self.rect_color[0] , self.rect_color[1], self.rect_color[2]*2)
        return 0

    def read_csv(self, path):
        data = []
        with open(path, 'r') as f:
                r = csv.reader(f)
                for row in r:
                    row = list(map(float, row))
                    data.append(row)
        return data

#w = 1024 #960
#h = 576 #540
#
#d = Detection(w,h)
#disp = Display(w,h)
#
#writing = False
#write_frames = 1000
#fourcc = cv2.VideoWriter_fourcc(*'H264')
#wvid = cv2.VideoWriter('detection_unet.mp4',fourcc,10.0,(w,h))
#
#fvs = FileVideoStream('videos/test.avi').start() #faster than cv2 videowriter
#print('Starting...')
#time.sleep(1.0)
#
#i = 0
#fps = FPS().start()
#while fvs.more():
#
#    if i == write_frames and writing:
#        break
#
#    cimg = fvs.read()
#    
#    cimg = cv2.resize(cimg, (w,h))
#    out = d.detect_nn(cimg)
#    #out = d.cheat_detect(cimg, i)
#    disp.paint(out)
#    fps.update()
#    fps.stop()
#    print('fps: %f at frame %i' % (fps.fps(),i))
#    if writing:
#        wvid.write(out)
#    i += 1
#
#if writing:
#    wvid.release()
#    print('Saved video.')
#
#cv2.destroyAllWindows()
#fvs.stop()
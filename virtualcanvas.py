import cv2
import numpy as np
import copy

# Open Camera
camera = cv2.VideoCapture(1)
img = np.zeros((1024, 1024, 3), np.uint8)
draw = True
erase = True
red = True
thickness = 10  # Thickness of the drawing
flag =0

while True:

    if flag == 0: #TOGGLES DRAW AND ERASE FOR FIRST TIME AFTER THAT IT DEPENDS ON USER
        flag = 1
        draw = not draw
        erase = not erase
        red = not red

    ret, frame = camera.read()
    if not ret:
        break  # Exit if the camera feed is not retrieved

    frame = cv2.resize(frame, (1024, 1024))
    frame = cv2.bilateralFilter(frame, 5, 50, 100)  # Smoothing
    frame = cv2.flip(frame, 1)  # Horizontal Flip
    #cv2.imshow('original', frame)

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower = np.array([0, 48, 80], dtype="uint8")
    upper = np.array([20, 255, 255], dtype="uint8")
    skinMask = cv2.inRange(hsv, lower, upper)
    #cv2.imshow('Threshold Hands', skinMask)

    # Getting the contours and convex hull
    skinMask1 = copy.deepcopy(skinMask)
    contours, hierarchy = cv2.findContours(skinMask1, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if contours:  # If contours are found
        maxArea = -1
        ci = 0
        for i in range(len(contours)):
            area = cv2.contourArea(contours[i])
            if area > maxArea:
                maxArea = area
                ci = i

        res = contours[ci]
        hull = cv2.convexHull(res)

        # Moments for centroid calculation
        M = cv2.moments(res)
        cX = int(M["m10"] / M["m00"]) if M["m00"] != 0 else 0
        cY = int(M["m01"] / M["m00"]) if M["m00"] != 0 else 0

        # Getting extreme points
        extLeft = tuple(res[res[:, :, 0].argmin()][0])
        extRight = tuple(res[res[:, :, 0].argmax()][0])
        extTop = tuple(res[res[:, :, 1].argmin()][0])
        extBot = tuple(res[res[:, :, 1].argmax()][0])

        # Draw contours and points
        cv2.drawContours(frame, [res], -1, (0, 255, 0), 2)
        cv2.drawContours(frame, [hull], -1, (0, 0, 255), 3)
        cv2.circle(frame, extLeft, 8, (0, 0, 255), -1)
        cv2.circle(frame, extRight, 8, (0, 255, 0), -1)
        cv2.circle(frame, extTop, 8, (100, 55, 100), -1)
        cv2.circle(frame, extBot, 8, (255, 255, 0), -1)
        cv2.circle(frame, (cX, cY), 7, (255, 255, 255), -1)
        cv2.putText(frame, "center", (cX - 20, cY - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

        # Draw on the image if drawing is enabled
        if draw:
            cv2.circle(img, extTop, thickness, (255, 255, 255), -1)  # Draw circle at fingertip position
            #cv2.circle(img, (extTop[0], extTop[1] + 10), thickness, (0, 55, 100), -1)  # Draw below fingertip
        if erase:
            cv2.circle(img, extTop, thickness, (0, 0, 0), 7)  # Draw circle at fingertip position
        if red:
            cv2.circle(img, extTop, thickness, (0, 0, 255), -1)  # Draw circle at fingertip position
            
    # Combine the canvas with the frame
    combined_frame = cv2.addWeighted(frame, 0.7, img, 0.3, 0)

    # Show the camera feed with drawing
    cv2.imshow('Camera Feed', combined_frame)

    k = cv2.waitKey(10)
    if k == 27:  # Press ESC to exit
        break    
    elif k == ord('n'):  # Press 'n' to clear the drawing
        img = np.zeros((1024, 1024, 3), np.uint8)  # Reset canvas
    elif k == ord('d'):  # Press 'd' to toggle drawing
        draw = not draw  # Toggle the draw flag
    elif k == ord('e'):  # Press 'e' to toggle erase
        erase = not erase
    elif k == ord('r'):  # Press 'r' to toggle red
        red = not red
    

# Release resources
camera.release()
cv2.destroyAllWindows()

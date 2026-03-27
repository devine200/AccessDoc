---
sidebar_position: 7
title: "4. Results and Discussions"
---


799 Rafael Bustamante-Alvarez et al. Water Supply Leak Detection Based...

The above formula is used to calculate the spectral power density and L=N to improve the resolution of the frequency representation. The units of spectral power density are Watts/Hertz.

The experiment is developed first by simulating the digital signal processing system for the process of capturing and processing the audio signal coming from the water leakage noises, this simulation is carried out using Simulink in Matlab. Then, Matlab programs are implemented in order to carry out the signal analysis process and subsequently a user interface is implemented with Matlab, in order to subsequently carry out the respective analyses to detect the water leakage.

## 4. Results and Discussions

Simulation of the acquisition and processing process

This simulation presents the digital signal processing system to capture and process the signals to analyse them by means of a device to observe the spectrum of the audio signal of the water leakage noise. The first block simulates the noise signal by reproducing the recorded noise signal which has been recorded at fs=44100Hz and 16-bit resolution.

The second block is the input filter which is a low-pass filter having an fc=fs/2, in this case fs=44100Hertz of eighth order elliptic type, representing the MAX293 IC with fc=22.05Khz, Rp=-0.15dB and Rs=-78dB with a transition ratio of 1.5 i.e. stop band frequency of 33.075Khz. The frequency response is shown in Fig. 7. Se observa un rizado de -0.15dB del rizado en la banda de paso del filtro pasabajo casi imperceptible y -78db en el rizado en la banda de supresión

Figure 7. Representation of the frequency response of the input low-pass filter

The third, fourth and fifth blocks are part of the analogue converter stage which has an fs=44100Hz and 16-bit resolution; in this stage the sampling (sample time=1/44100), quantization (Quantization interval=2/2^16) and coding processes are carried out. The sixth

## Nanotechnology Perceptions Vol. 20 No. S9 (2024)

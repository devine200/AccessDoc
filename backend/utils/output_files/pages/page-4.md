# Page 4

Water Supply Leak Detection Based…  Rafael Bustamante-Alvarez et al. 796

## Figure 2. Digital signal processing system

Digital signal processing is a process of signal analysis or signal transformation depending on its application, in this case it is the analysis of the audio signal, for which digital audio signal processing hardware is required, the stages of which are described as follows:

• Input filter: It is a low-pass filter, whose cutoff frequency is half the sampling frequency (fs) of the analogue-to-digital converter of the next stage. This filter ensures that aliasing of the processed signal does not occur.

• Analogue-to-digital converter: This stage consists of an element whose function is to digitise the audio signal. That is to say, to convert the analogue signal into a digital signal, for which the processes of sampling, quantisation and coding are carried out. A quantization level is a voltage level that the converter assigns to each sample, the quantization levels are a function of the number of bits that each analogue-digital converter has. On the other hand, in encoding, each quantization level is assigned a binary value (bits per sample).

• Signal processor: This stage executes the program that allows to analyse or transform the digitised signal coming from the analogue-digital converter. This is usually a personal computer or a specialised card for signal processing. This program incorporates an algorithm such as the Fast Fourier Transform for the case of audio signal processing. The processed signal, represented by data (samples), is sent to the digital analogue conversion stage.

• Analogue Digital Converter: The processed signal as data stream is converted to an analogue signal at an amplitude level corresponding to each sample. This results in a stepped signal with the waveform pattern of the processed signal, so it must be taken to a subsequent filtering process.

• Output filter: This low-pass filter is responsible for smoothing the processed signal, removing the step effect. It removes harmonics from the frequency spectrum of the stepped signal.  This process of removing these unwanted components is called smoothing.

## Sections of the digital signal processing system

## The system consists of the following sections:

• Signal acquisition section: Firstly, the audio signal coming from the microphone must be amplified in accordance with the dynamic range requirement of the analogue-digital converter. Also, its maximum frequency must be half the sampling frequency of 44.1KHz of the analogue-digital converter. This frequency is considered because it is compatible with the different audio systems. The pick-up stage consists of an anti-aliasing filter and a digital analogue converter with a sampling frequency of 44.1Khz.  In this stage the audio signal is converted into samples.

## Nanotechnology Perceptions Vol. 20 No. S9 (2024)

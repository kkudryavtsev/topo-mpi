"""
Pattern generators for audio signals.

$Id$
"""
__version__='$Revision$'


import param
import os

from param.parameterized import ParamOverrides
from topo.pattern.basic import TimeSeries, Spectrogram, PowerSpectrum
from topo.base.patterngenerator import PatternGenerator

from numpy import arange, array, ceil, complex64, concatenate, cos, exp, fft, float32, floor, hanning, hstack, log, log10, logspace, multiply, ones, pi, repeat, reshape, shape, size, sqrt, sum, tile, where, zeros
         
try:
    import matplotlib.ticker
    import pylab
    
except ImportError:
    param.Parameterized(name=__name__).warning("Could not import matplotlib; module will not be useable.")
    from basic import ImportErrorRaisingFakeModule
    pylab = ImportErrorRaisingFakeModule("matplotlib")
    
try:
    import scikits.audiolab as audiolab

except ImportError:
    param.Parameterized().warning("audio.py classes will not be usable;" \
        "scikits.audiolab is not available.")
        
        
class AudioFile(TimeSeries):
    """
    Requires an audio file in any format accepted by audiolab (wav, aiff,
    flac).
    """
    
    # See TimeSeries itself for a detailed description of abstract status
    _abstract = True
        
    time_series = param.Parameter(precedence=(-1))
    sample_rate = param.Number(precedence=(-1))
    
    filename = param.Filename(default='sounds/complex/daisy.wav', doc="""
        File path (can be relative to Topographica's base path) to an
        audio file. The audio can be in any format accepted by audiolab, 
        e.g. WAV, AIFF, or FLAC.
        """)
            
    def __init__(self, **params):
        super(AudioFile, self).__init__(**params)
        self._setParams(**params)
        
        self._loadAudioFile()
        
    def _setParams(self, **params):
        super(AudioFile, self)._setParams(**params)

        for parameter,value in params.items():
            setattr(self, parameter, value)
            
            if parameter == "filename":
                self._loadAudioFile()
                
    def _loadAudioFile(self):
        self.source = audiolab.Sndfile(self.filename, 'r')
        
        self._setParams(time_series=self.source.read_frames(self.source.nframes, dtype=float32)) 
        self._setParams(sample_rate=self.source.samplerate)
        
    def __firstCall__(self, **params):
        self._setParams(**params)        
        super(AudioFile, self).__firstCall__(**params)    

    def __everyCall__(self, **params):
        return self._extractNextInterval()


class AudioFolder(AudioFile):
    """
    Returns a rolling spectrogram, i.e. the spectral density over time 
    of a rolling window of the input audio signal, for all files in the 
    specified folder.
    """
    
    # See AudioFile itself for a detailed description of abstract status
    _abstract = True
    
    filename = param.Filename(precedence=(-1))

    folderpath=param.Foldername(default='sounds/complex', 
        doc="""Folder path (can be relative to Topographica's base path) to a
        folder containing audio files. The audio can be in any format accepted 
        by audiolab, i.e. WAV, AIFF, or FLAC.""")
         
    gap_between_sounds=param.Number(default=0.0, bounds=(0.0,None),
        doc="""The gap in seconds to insert between consecutive soundfiles.""")
                 
    def __init__(self, **params):
        super(AudioFolder, self).__init__(**params)
        self._setParams(**params)
    
    def _setParams(self, **params):
        super(AudioFolder, self)._setParams(**params)

        for parameter,value in params.items():
            setattr(self, parameter, value)
                
    def _loadAudioFolder(self):
        folder_contents = os.listdir(self.folderpath)
        self.sound_files = []
        
        for file in folder_contents:
            if file[-4:]==".wav" or file[-3:]==".wv" or file[-5:]==".aiff" or file[-4:]==".aif" or file[-5:]==".flac":
                self.sound_files.append(self.folderpath + "/" + file) 

        self._setParams(filename=self.sound_files[0])        
        self.next_file = 1

    def _extractNextInterval(self):
        interval_start = self._next_interval_start
        interval_end = interval_start + self.samples_per_interval

        if interval_end > self.time_series.size:
        
            if self.next_file < len(self.sound_files):
                next_source = audiolab.Sndfile(self.sound_files[self.next_file], 'r')
                self.next_file += 1
     
                if next_source.samplerate != self.sample_rate:
                    raise ValueError("All sound files must be of the same sample rate")
            
                next_time_series = hstack((self.time_series[interval_start:self.time_series.size], self.inter_signal_gap))
                next_time_series = hstack((next_time_series, next_source.read_frames(next_source.nframes, dtype=float32)))
                self.time_series = next_time_series
                
                self._next_interval_start = interval_start = 0   
                interval_end = self.samples_per_interval
        
            else:
                if interval_start < self.time_series.size:
                    if self.repeat:
                        self._next_interval_start = 0
                    else:
                        self.warning("Returning last interval of the time series.")
                        self._next_interval_start = self.time_series.size
                    
                    remaining_signal = self.time_series[interval_start:self.time_series.size]
                    return hstack((remaining_signal, zeros(self.samples_per_interval-remaining_signal.size)))
                
                else:
                    raise ValueError("Reached the end of the time series.")
        
        self._next_interval_start += int(self.seconds_per_iteration*self.sample_rate)
        return self.time_series[interval_start:interval_end]

    def __firstCall__(self, **params):
        self._setParams(**params)
        self._loadAudioFolder()
        
        super(AudioFile, self).__firstCall__(**params)
        self.inter_signal_gap = zeros(int(self.gap_between_sounds*self.sample_rate), dtype=float32)

    def __everyCall__(self, **params):
        return self._extractNextInterval()
                

class AuditorySpectrogram(Spectrogram):
    """
    Extends Spectrogram to provide a response in decibels over an octave scale.
    """
        
    def _setFrequencySpacing(self, index_of_min_freq, index_of_max_freq):
        self.frequency_index_spacing = ceil(logspace(log10(index_of_max_freq), log10(index_of_min_freq), 
            num=(index_of_max_freq-index_of_min_freq), endpoint=True, base=10))
                
    def _convertToDecibels(self, amplitudes):
        amplitudes[amplitudes==0] = 1.0
        return (20.0 * log10(abs(amplitudes)))
        
    def __firstCall__(self, **params):
        super(AuditorySpectrogram, self).__firstCall__(**params)
    
    def __everyCall__(self, **params):
        self._updateSpectrogram(self._convertToDecibels(self._getAmplitudes()))
        
        return self._spectrogram


class AuditorySpectrogramSimpleOuterEar(AuditorySpectrogram):
    """
    Extends Spectrogram with a simple model of outer ear amplification. 
    One can set both the range to amplify and the amount.
    """
        
    amplify_from_frequency=param.Number(default=1000.0, bounds=(0.0,None),
        doc="""The lower bound of the frequency range to be amplified.""")

    amplify_till_frequency=param.Number(default=7000.0, bounds=(0.0,None),
        doc="""The upper bound of the frequency range to be amplified.""")
    
    amplify_by_percentage=param.Number(default=3.0, bounds=(0.0,None),
        doc="""The percentage by which to amplify the signal between the 
        specified frequency range.""")
        
    def _setParams(self, **params):
        super(AuditorySpectrogramSimpleOuterEar, self)._setParams(**params)
        
        for parameter,value in params.items():
            if parameter=="amplify_from_frequency" or parameter=="amplify_till_frequency" or parameter=="amplify_by_percentage":
                if value < 0:
                    raise ValueError("Cannot have a negative value for amplify_from_frequency, amplify_till_frequency, or amplify_by_percentage.")
                else:
                    setattr(self, parameter, value)
            
        if self.amplify_from_frequency > self.amplify_till_frequency:
            raise ValueError("AuditorySpectrogramSimpleOuterEar's amplify from must be less than its amplify till.")

    def __firstCall__(self, **params):
        super(AuditorySpectrogramSimpleOuterEar, self).__firstCall__(**params)
        
    def __everyCall__(self, **params):
        amplitudes = self._getAmplitudes()
        
        self.sheet_frequency_divisions = logspace(log10(self.max_frequency), log10(self.min_frequency), 
            num=self._sheet_dimensions[0], endpoint=True, base=10)
            
        if self.amplify_by_percentage > 0:
            if (self.amplify_from_frequency < self.min_frequency) or (self.amplify_from_frequency > self.max_frequency):
                raise ValueError("Lower bound of frequency to amplify is outside the global frequency range.")
 
            elif (self.amplify_till_frequency < self.min_frequency) or (self.amplify_till_frequency > self.max_frequency):
                raise ValueError("Upper bound of frequency to amplify is outside the global frequency range.")
            
            else:
                amplify_between = [ frequency for frequency in self.sheet_frequency_divisions \
                    if frequency <= self.amplify_till_frequency and frequency >= self.amplify_from_frequency ]
                                
                # the larger the index, the lower the frequency.
                amplify_start_index = where(self.sheet_frequency_divisions == max(amplify_between))[0][0]
                amplify_end_index = where(self.sheet_frequency_divisions == min(amplify_between))[0][0]
                
                # build an array of equal length to amplitude array, containing percentage amplifications.
                amplified_range = 1.0 + hanning(amplify_end_index-amplify_start_index+1) * self.amplify_by_percentage/100.0
                amplify_by = concatenate((ones(amplify_start_index), amplified_range, ones(len(self.sheet_frequency_divisions)-amplify_end_index-1))).reshape((-1, 1))
                
                amplitudes = multiply(amplitudes, amplify_by)
        
        self._updateSpectrogram(self._convertToDecibels(amplitudes))
        return self._spectrogram
        

class LyonsCochlearModel(PowerSpectrum):
    """
    Outputs a cochlear decomposition as a set of frequency responses of linear 
    band-pass filters. Employs Lyons Cochlear Model to do so.
    
    R. F. Lyon, "A computational model of filtering, detection and compression
    in the cochlea." in Proc. of the IEEE Int. Conf. Acoust., Speech, Signal
    Processing, Paris, France, May 1982.
        
    Specific implementation details can be found in: 
    
    Malcolm Slaney, "Lyon's Cochlear Model, in Advanced Technology Group,
    Apple Technical Report #13", 1988.
    """
    
    signal = param.Parameter(default=None, doc="""
        A TimeSeries object to be fed to the model.
        
        This can be any kind of signal, be it from audio files or live
        from a mic, as long as the values conform to a TimeSeries.
        """)
    
    quality_factor = param.Number(default=8.0, doc="""
        Quality factor controls the bandwidth of each cochlear filter.
        
        The bandwidth of each cochlear filter is a function of its 
        center frequency. At high frequencies the bandwidth is 
        approximately equal to the center frequency divided by a 
        quality constant (quality_factor). At lower frequncies the 
        bandwidth approaches a constant given by: 1000/quality_factor.
        """)
    
    stage_overlap_factor = param.Number(default=4.0, doc="""
        The degree of overlap between filters.
    
        Successive filter stages are overlapped by a fraction of their 
        bandwidth. The number is arbitrary but smaller numbers lead to 
        more computations. We currently overlap 4 stages within the 
        bandpass region of any one filter.
        """)
                
    def __init__(self, **params):
        super(LyonsCochlearModel, self).__init__(**params)
        self._setParams(**params)
        
        # Hardwired Parameters specific to model, which is to say changing
        # them without knowledge of the mathematics of the model is a bad idea.
        self.sample_rate = self.signal.sample_rate
        self.half_sample_rate = float32(self.sample_rate/2.0)
        self.quart_sample_rate = float32(self.half_sample_rate/2.0)
 
        self.ear_q = float32(self.quality_factor)
        self.ear_step_factor = float32(1.0/self.stage_overlap_factor)

        self.ear_break_f = float32(1000.0)
        self.ear_break_squared = self.ear_break_f*self.ear_break_f

        self.ear_preemph_corner_f = float32(300.0)
        self.ear_zero_offset = float32(1.5)
        self.ear_sharpness = float32(5.0)
        
        self._generateCochlearFilters()
        self._first_call = True
        
    def _setParams(self, **params):
        super(LyonsCochlearModel, self)._setParams(**params)
        
        for parameter,value in params.items():
            setattr(self,parameter,value)
    
    def _earBandwidth(self, cf):
        return sqrt(cf*cf + self.ear_break_squared) / self.ear_q
        
    def _maxFrequency(self):
        bandwidth_step_max_f = self._earBandwidth(self.half_sample_rate) * self.ear_step_factor    
        return self.half_sample_rate + bandwidth_step_max_f - bandwidth_step_max_f*self.ear_zero_offset

    def _numOfChannels(self):
        min_f = self.ear_break_f / sqrt(4.0*self.ear_q*self.ear_q - 1.0)
        channels = log(self.max_f_calc) - log(min_f + sqrt(min_f*min_f + self.ear_break_squared))
        
        return int(floor(self.ear_q*channels/self.ear_step_factor))

    def _calcCentreFrequenciesTill(self, channel_index):
        if (self.centre_frequencies[channel_index] > 0):
            return self.centre_frequencies[channel_index]
        else:
            step = self._calcCentreFrequenciesTill(channel_index-1)
            channel_cf = step - self.ear_step_factor*self._earBandwidth(step)
            self.centre_frequencies[channel_index] = channel_cf
            
            return channel_cf

    def _evaluateFiltersForFrequencies(self, filters, frequencies):
        Zs = exp(2j*pi*frequencies/self.sample_rate)
        Z_squareds = Zs * Zs
        
        zeros = ones((shape(frequencies)[0], shape(filters[0])[0], 3), dtype=complex64)
        zeros[:,:,2] = filters[0][:,2] * Z_squareds
        zeros[:,:,1] = filters[0][:,1] * Zs
        zeros[:,:,0] = filters[0][:,0]
        zeros = sum(zeros, axis=2)

        poles = ones((shape(frequencies)[0], shape(filters[1])[0], 3), dtype=complex64)
        poles[:,:,2] = filters[1][:,2] * Z_squareds
        poles[:,:,1] = filters[1][:,1] * Zs
        poles[:,:,0] = filters[1][:,0]
        poles = sum(poles, axis=2)
        
        return zeros / poles
        
    # a frequency and gain are specified so that the resulting filter can 
    # be normalized to have any desired gain at a specified frequency.
    def _makeFilters(self, zeros, poles, f, desired_gains):  
        desired_gains = reshape(desired_gains,[size(desired_gains),1])
        
        unit_gains = self._evaluateFiltersForFrequencies([zeros,poles], f)
        unit_gains = reshape(unit_gains,[size(unit_gains),1])
        
        return [zeros*desired_gains, poles*unit_gains]
        
    def _frequencyResponses(self, evaluated_filters):
        evaluated_filters[evaluated_filters==0] = 1.0
        return 20.0 * log10(abs(evaluated_filters))

    def _specificFilter(self, x2_coefficient, x_coefficient, constant):  
        return array([[x2_coefficient,x_coefficient,constant], ], dtype=float32)
            
    def _firstOrderFilterFromCorner(self, corner_f):
        polynomial = zeros((1,3), dtype=float32)
        polynomial[:,0] = -exp(-2.0*pi*corner_f/self.sample_rate)
        polynomial[:,1] = 1.0

        return polynomial

    def _secondOrderFilterFromCenterQ(self, cf, quality):
        cf_as_ratio = cf/self.sample_rate
        
        rho = exp(-pi*cf_as_ratio/quality)
        rho_squared = rho*rho
        
        theta = 2.0*pi*cf_as_ratio * sqrt(1.0-1.0/(4.0*quality*quality))
        theta_calc = -2.0*rho*cos(theta)
        
        polynomial = ones((size(cf),3), dtype=float32)
        polynomial[:,1] = theta_calc
        polynomial[:,2] = rho_squared
        
        return polynomial
     
    def _earFilterGains(self):
        return self.centre_frequencies[:-1] / self.centre_frequencies[1:]

    def _earFirstStage(self):    
        outer_middle_ear_filter = self._makeFilters(self._firstOrderFilterFromCorner(self.ear_preemph_corner_f), 
            self._specificFilter(1.0,0.0,0.0), array([0.0]), 1.0)

        high_freq_compensator = self._makeFilters(self._specificFilter(1.0,0.0,-1.0), self._specificFilter(0.0,0.0,1.0), 
            array([self.quart_sample_rate]), 1.0)
        
        pole_pair = self._makeFilters(self._specificFilter(0.0,0.0,1.0), 
            self._secondOrderFilterFromCenterQ(self.cascade_pole_cfs[0],self.cascade_pole_qs[0]), 
            array([self.quart_sample_rate]), 1.0)
        
        outer_middle_ear_evaluations = self._evaluateFiltersForFrequencies(outer_middle_ear_filter, self.frequencies)
        high_freq_compensator_evaluations = self._evaluateFiltersForFrequencies(high_freq_compensator, self.frequencies)
        pole_pair_evaluations = self._evaluateFiltersForFrequencies(pole_pair, self.frequencies)
        
        return outer_middle_ear_evaluations * high_freq_compensator_evaluations * pole_pair_evaluations

    def _earAllOtherStages(self):
        zeros = self._secondOrderFilterFromCenterQ(self.cascade_zero_cfs[1:], self.cascade_zero_qs[1:])
        poles = self._secondOrderFilterFromCenterQ(self.cascade_pole_cfs[1:], self.cascade_pole_qs[1:])
        
        stage_filters = self._makeFilters(zeros, poles, array([0.0]), self.ear_filter_gains)
        return self._evaluateFiltersForFrequencies(stage_filters, self.frequencies)

    def _generateCascadeFilters(self):
        
        cascade_filters = self.ear_stages
        
        for channel in range(1,self.num_of_channels):
            cascade_filters[channel,:] = cascade_filters[channel,:] * cascade_filters[channel-1,:]
        
        return self._frequencyResponses(cascade_filters)
        
    def _generateCochlearFilters(self):
        max_f = self._maxFrequency()
        self.max_f_calc = max_f + sqrt(max_f*max_f + self.ear_break_squared)

        self.num_of_channels = self._numOfChannels()

        self.centre_frequencies = zeros(self.num_of_channels, dtype=float32)
        self.centre_frequencies[0] = max_f
        self._calcCentreFrequenciesTill(self.num_of_channels-1)

        bandwidths = self._earBandwidth(self.centre_frequencies)
        
        self.cascade_zero_cfs = self.centre_frequencies + bandwidths*self.ear_step_factor*self.ear_zero_offset
        self.cascade_zero_qs = self.ear_sharpness * self.cascade_zero_cfs / bandwidths
        self.cascade_pole_cfs = self.centre_frequencies
        self.cascade_pole_qs = self.centre_frequencies / bandwidths
        
        self.ear_filter_gains = self._earFilterGains()
        
        self.frequencies = arange(self.half_sample_rate).reshape(self.half_sample_rate, 1)
        
        self.ear_stages = hstack((self._earFirstStage(), self._earAllOtherStages())).transpose() 
        
        self.cochlear_channels = self._generateCascadeFilters()
        
    def _getAmplitudes(self):
        """
        Perform a real Discrete Fourier Transform (DFT; implemented
        using a Fast Fourier Transform algorithm, FFT) of the current
        sample from the signal multiplied by the smoothing window.

        See numpy.rfft for information about the Fourier transform.
        """
        
        sample_rate = self.signal.sample_rate        
        
        # A signal window *must* span one sample rate, irrespective of interval length.
        signal_window = tile(self.signal(), ceil(sample_rate/self.signal.samples_per_interval))
        
        if self.windowing_function == None:
            smoothed_window = signal_window[0:sample_rate]
        else:
            smoothed_window = signal_window[0:sample_rate] * self.windowing_function(sample_rate)  
        
        return abs(fft.rfft(smoothed_window))[0:sample_rate/2]
                
    def __firstCall__(self, **params):
        self._setParams(**params)
        super(LyonsCochlearModel, self).__firstCall__(**params)
        
        if self._sheet_dimensions[0] != self.num_of_channels:
            raise ValueError("The number of Sheet Rows must correspond to the number of Lyons Filters. Adjust the number sheet rows from [%s] to [%s]." 
                %(self._sheet_dimensions[0], self.num_of_channels))
    
    def __everyCall__(self, **params):
        sample_rate = self.signal.sample_rate
        amplitudes = self._getAmplitudes().reshape(1, sample_rate/2.0)
        
        filter_responses = multiply(self.cochlear_channels, amplitudes)
        sheet_responses = zeros(self.num_of_channels)
        
        for channel in range(0, self.num_of_channels):
            time_responses = abs(fft.ifft(filter_responses[channel]))
            sheet_responses[channel] = sum(time_responses) / (sample_rate/2.0) 
        
        sheet_responses = sheet_responses.reshape(self.num_of_channels, 1)

        if self._sheet_dimensions[1] > 1:
            sheet_responses = repeat(sheet_responses, self._sheet_dimensions[1], axis=1)

        return sheet_responses
        
        
class Cochleogram(LyonsCochlearModel):
    """
    Employs Lyons Cochlear Model to return a Cochleoogram, 
    i.e. the response over time along the cochlea.
    """
        
    def _updateCochleogram(self, amplitudes):
        self._cochleogram = hstack((amplitudes, self._cochleogram))
        self._cochleogram = self._cochleogram[0:, 0:self._cochleogram.shape[1]-1]
                
    def __firstCall__(self, **params):
        super(Cochleogram, self).__firstCall__(**params)
        self._cochleogram = zeros(self._sheet_dimensions)

    def __everyCall__(self, **params):
        sample_rate = self.signal.sample_rate
        amplitudes = self._getAmplitudes().reshape(1, sample_rate/2.0)
        
        filter_responses = multiply(self.cochlear_channels, amplitudes)
        sheet_responses = zeros(self.num_of_channels)
        
        for channel in range(0, self.num_of_channels):
            time_responses = abs(fft.ifft(filter_responses[channel]))
            sheet_responses[channel] = sum(time_responses) / (sample_rate/2.0) 
        
        sheet_responses = sheet_responses.reshape(self.num_of_channels, 1)

        self._updateCochleogram(sheet_responses)
        return self._cochleogram
        
        
        
if __name__=='__main__' or __name__=='__mynamespace__':

    from topo import sheet
    import topo

    topo.sim['C']=sheet.GeneratorSheet(
        input_generator=AudioFile(filename='sounds/complex/daisy.wav',sample_window=0.3,
            seconds_per_timestep=0.3,min_frequency=20,max_frequency=20000),
            nominal_bounds=sheet.BoundingBox(points=((-0.1,-0.5),(0.0,0.5))),
            nominal_density=10,period=1.0,phase=0.05)

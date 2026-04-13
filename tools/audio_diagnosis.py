
import sounddevice as sd
import numpy as np
import time
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("AudioTest")

def main():
    logger.info("=== Audio Diagnosis Tool ===")
    
    # 1. List Devices
    logger.info("1. Enumerating Devices...")
    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if not input_devices:
            logger.error("❌ No Input Devices Found!")
            return
            
        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                logger.info(f"   [{i}] {d['name']} (Ch: {d['max_input_channels']}, Rate: {d['default_samplerate']})")
                
    except Exception as e:
        logger.error(f"❌ Device Enumeration Failed: {e}")
        return

    # 2. Test Capture (Default Device)
    logger.info("\n2. Testing Capture (System Default) - 3 Seconds...")
    
    try:
        duration = 3  # seconds
        fs = 16000
        
        logger.info("   🎤 Recording...")
        
        # Simple blocking record
        myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1, blocking=True)
        
        logger.info("   ✅ Recording Complete.")
        
        # 3. Analyze Audio
        rms = np.sqrt(np.mean(myrecording**2))
        max_amp = np.max(np.abs(myrecording))
        
        logger.info(f"\n3. Analysis:")
        logger.info(f"   RMS (Volume): {rms:.6f}")
        logger.info(f"   Max Amplitude: {max_amp:.6f}")
        
        if rms < 0.001:
            logger.warning("   ⚠️ Audio is extremely quiet (Silent). Check Mic Mute/Gain!")
        else:
            logger.info("   ✅ Audio detected successfully.")
            
    except Exception as e:
         logger.error(f"❌ Capture Failed: {e}")

if __name__ == "__main__":
    main()

import argparse
import os
import pandas as pd
import torchaudio
import torch
import csv
from tqdm import tqdm
import shutil

def prepare_commonvoice(args):
    """
    Process Mozilla Common Voice dataset for training.
    Assumes you've already downloaded the dataset from https://commonvoice.mozilla.org/
    """
    print(f"Processing Common Voice dataset from {args.input_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(os.path.join(args.output_dir, "clips"), exist_ok=True)
    
    # Load the validated.tsv file
    tsv_path = os.path.join(args.input_dir, "validated.tsv")
    print(f"Loading data from {tsv_path}")
    df = pd.read_csv(tsv_path, delimiter='\t', quoting=csv.QUOTE_NONE)
    
    # Filter by various criteria
    if args.max_duration:
        df = df[df['duration'] <= args.max_duration]
    
    if args.min_duration:
        df = df[df['duration'] >= args.min_duration]
    
    # Create a new dataframe for the processed data
    processed_data = []
    
    # Process each clip
    print(f"Processing {len(df)} clips...")
    for idx, row in tqdm(df.iterrows(), total=len(df)):
        clip_path = os.path.join(args.input_dir, "clips", row['path'])
        
        try:
            # Load and resample audio
            waveform, sample_rate = torchaudio.load(clip_path)
            
            # Convert to mono
            if waveform.size(0) > 1:
                waveform = waveform.mean(dim=0, keepdim=True)
            
            # Resample to 24kHz
            if sample_rate != 24000:
                waveform = torchaudio.functional.resample(waveform, orig_freq=sample_rate, new_freq=24000)
            
            # Check audio quality if needed
            if args.filter_quality:
                # Simple quality check: ensure audio is not too quiet or too loud
                peak = waveform.abs().max().item()
                if peak < 0.01 or peak > 0.99:
                    continue
            
            # Save processed audio
            output_path = os.path.join(args.output_dir, "clips", row['path'])
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            torchaudio.save(output_path, waveform, 24000)
            
            # Add to processed data
            processed_data.append({
                'path': row['path'],
                'sentence': row['sentence'],
                'duration': waveform.size(1) / 24000
            })
            
            if len(processed_data) >= args.max_samples and args.max_samples > 0:
                print(f"Reached maximum sample count: {args.max_samples}")
                break
                
        except Exception as e:
            print(f"Error processing {clip_path}: {e}")
            continue
    
    # Create new TSV file
    output_tsv = os.path.join(args.output_dir, "processed.tsv")
    pd.DataFrame(processed_data).to_csv(output_tsv, sep='\t', index=False)
    
    # Create train-test split
    if args.test_size > 0:
        df_processed = pd.DataFrame(processed_data)
        
        # Simple random split
        test_df = df_processed.sample(frac=args.test_size)
        train_df = df_processed.drop(test_df.index)
        
        # Save splits
        train_df.to_csv(os.path.join(args.output_dir, "train.tsv"), sep='\t', index=False)
        test_df.to_csv(os.path.join(args.output_dir, "test.tsv"), sep='\t', index=False)
        
        print(f"Train set: {len(train_df)} samples")
        print(f"Test set: {len(test_df)} samples")
    
    print(f"Processed {len(processed_data)} clips successfully.")
    print(f"Output TSV file: {output_tsv}")

def main():
    parser = argparse.ArgumentParser(description="Process Mozilla Common Voice dataset for training")
    parser.add_argument("--input_dir", type=str, required=True, 
                        help="Input directory containing Common Voice dataset")
    parser.add_argument("--output_dir", type=str, required=True, 
                        help="Output directory for processed data")
    parser.add_argument("--max_duration", type=float, default=10.0, 
                        help="Maximum audio duration in seconds")
    parser.add_argument("--min_duration", type=float, default=1.0, 
                        help="Minimum audio duration in seconds")
    parser.add_argument("--filter_quality", action="store_true", 
                        help="Apply quality filtering")
    parser.add_argument("--test_size", type=float, default=0.1, 
                        help="Fraction of data to use for testing")
    parser.add_argument("--max_samples", type=int, default=-1, 
                        help="Maximum number of samples to process (-1 for all)")
    
    args = parser.parse_args()
    prepare_commonvoice(args)

if __name__ == "__main__":
    main()

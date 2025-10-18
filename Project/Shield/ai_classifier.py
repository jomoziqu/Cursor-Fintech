import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import os
from typing import Dict, Tuple

class TransactionClassifier:
    def __init__(self):
        self.model = None
        self.categories = {
            'medical': {'is_emergency': True, 'priority': 9},
            'school_fees': {'is_emergency': True, 'priority': 8},
            'family_emergency': {'is_emergency': True, 'priority': 9},
            'repair': {'is_emergency': True, 'priority': 6},
            'entertainment': {'is_emergency': False, 'priority': 2},
            'shopping': {'is_emergency': False, 'priority': 3},
            'airtime': {'is_emergency': False, 'priority': 4}
        }
        
        # Load or train model
        if os.path.exists('transaction_classifier.pkl'):
            self.model = joblib.load('transaction_classifier.pkl')
        else:
            self._train_model()
    
    def _get_training_data(self):
        """Generate training data for Kenyan context"""
        training_data = [
            # Medical emergencies
            ("hospital bill for mama", "medical"),
            ("doctor visit urgent", "medical"),
            ("medicine for child", "medical"),
            ("surgery payment", "medical"),
            ("clinic fees", "medical"),
            ("ambulance service", "medical"),
            ("medical emergency", "medical"),
            ("health insurance", "medical"),
            ("prescription drugs", "medical"),
            ("dental treatment", "medical"),
            
            # School fees
            ("school fees payment", "school_fees"),
            ("tuition for semester", "school_fees"),
            ("exam fees", "school_fees"),
            ("school uniform", "school_fees"),
            ("textbooks", "school_fees"),
            ("education expenses", "school_fees"),
            ("university fees", "school_fees"),
            ("school transport", "school_fees"),
            ("graduation fees", "school_fees"),
            ("school trip", "school_fees"),
            
            # Family emergencies
            ("funeral expenses", "family_emergency"),
            ("family emergency", "family_emergency"),
            ("urgent family matter", "family_emergency"),
            ("burial costs", "family_emergency"),
            ("family crisis", "family_emergency"),
            ("emergency travel home", "family_emergency"),
            ("family member accident", "family_emergency"),
            ("urgent family support", "family_emergency"),
            
            # Repairs
            ("phone repair", "repair"),
            ("car repair", "repair"),
            ("house repair", "repair"),
            ("laptop fix", "repair"),
            ("motorcycle repair", "repair"),
            ("roof repair", "repair"),
            ("plumbing fix", "repair"),
            ("electrical repair", "repair"),
            ("appliance repair", "repair"),
            
            # Entertainment (non-emergency)
            ("movie tickets", "entertainment"),
            ("party expenses", "entertainment"),
            ("drinks with friends", "entertainment"),
            ("club entry", "entertainment"),
            ("concert tickets", "entertainment"),
            ("weekend fun", "entertainment"),
            ("entertainment", "entertainment"),
            ("leisure activity", "entertainment"),
            ("vacation", "entertainment"),
            
            # Shopping (non-emergency)
            ("new clothes", "shopping"),
            ("shopping spree", "shopping"),
            ("buy shoes", "shopping"),
            ("purchase items", "shopping"),
            ("new gadget", "shopping"),
            ("shopping mall", "shopping"),
            ("buy stuff", "shopping"),
            ("retail therapy", "shopping"),
            ("new phone", "shopping"),
            
            # Airtime (non-emergency)
            ("airtime top up", "airtime"),
            ("data bundles", "airtime"),
            ("phone credit", "airtime"),
            ("internet bundles", "airtime"),
            ("mobile money", "airtime"),
            ("communication", "airtime"),
            ("phone bills", "airtime"),
        ]
        
        texts, labels = zip(*training_data)
        return list(texts), list(labels)
    
    def _train_model(self):
        """Train the classification model"""
        texts, labels = self._get_training_data()
        
        # Create pipeline with TF-IDF and Naive Bayes
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(lowercase=True, stop_words='english', ngram_range=(1, 2))),
            ('classifier', MultinomialNB(alpha=1.0))
        ])
        
        # Train the model
        self.model.fit(texts, labels)
        
        # Save the model
        joblib.dump(self.model, 'transaction_classifier.pkl')
        print("Model trained and saved successfully!")
    
    def classify_transaction(self, description: str) -> Dict:
        """Classify a transaction description"""
        if not self.model:
            raise ValueError("Model not loaded or trained")
        
        # Clean and prepare text
        description = description.lower().strip()
        
        # Get prediction and probabilities
        prediction = self.model.predict([description])[0]
        probabilities = self.model.predict_proba([description])[0]
        
        # Get confidence score
        confidence = float(max(probabilities))
        
        # Get category info
        category_info = self.categories.get(prediction, {'is_emergency': False, 'priority': 1})
        
        return {
            'category': prediction,
            'confidence': confidence,
            'is_emergency': category_info['is_emergency'],
            'priority_score': category_info['priority'],
            'recommendation': self._get_recommendation(prediction, confidence)
        }
    
    def _get_recommendation(self, category: str, confidence: float) -> str:
        """Generate recommendation based on classification"""
        if confidence < 0.7:
            return "Classification uncertain. Please review manually."
        
        if category in ['medical', 'family_emergency']:
            return "High priority emergency detected. Shielded loan recommended."
        elif category in ['school_fees', 'repair']:
            return "Important expense detected. Consider shielded loan if urgent."
        else:
            return "Non-emergency expense. Consider if this aligns with your savings goals."

# Global classifier instance
classifier = TransactionClassifier()
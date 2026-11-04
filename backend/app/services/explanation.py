from typing import Dict, Any

class ExplanationGenerator:
    """
    Générateur d'explications en Français et Darija à partir d'un JSON agronomique.
    Évite de surcharger l'agriculteur avec des chiffres inutiles.
    """

    @staticmethod
    def generate_french(data: Dict[str, Any]) -> str:
        irrigation = data.get("irrigation_recommendation", {})
        fungal = data.get("fungal_risk", {})
        weather = data.get("weather_summary", {})
        crop = data.get("crop_type", "votre parcelle")

        sentences = []

        # Recommandation d'irrigation
        if irrigation.get("action") == "IRRIGATE":
            duration = irrigation.get("duration_hours", 0)
            sentences.append(f"Il est recommandé d'irriguer votre culture de {crop} pendant environ {duration} heures aujourd'hui.")
        else:
            sentences.append(f"Pas besoin d'irriguer votre culture de {crop} aujourd'hui, le sol dispose d'une humidité suffisante.")

        # Alerte risque fongique / météo
        if fungal.get("level") == "HIGH":
            sentences.append("Attention, le risque de maladies (champignons) est élevé à cause de l'humidité.")
        elif fungal.get("level") == "MEDIUM":
            sentences.append("Un risque modéré de maladie est détecté, restez vigilant.")

        if weather.get("spray_blocked"):
            sentences.append("Évitez tout traitement par pulvérisation aujourd'hui en raison du vent fort.")

        return " ".join(sentences)

    @staticmethod
    def generate_darija(data: Dict[str, Any]) -> str:
        irrigation = data.get("irrigation_recommendation", {})
        fungal = data.get("fungal_risk", {})
        weather = data.get("weather_summary", {})

        sentences = []

        # Irrigation en Darija
        if irrigation.get("action") == "IRRIGATE":
            duration = irrigation.get("duration_hours", 0)
            sentences.append(f"من الأفضل تسقي الضايعة ديالك اليوم لمدة {duration} سوايع.")
        else:
            sentences.append("ماحتاجش تسقي اليوم، الأرض باقي فيها الماء كافي.")

        # Risque fongique
        if fungal.get("level") == "HIGH":
            sentences.append("رد بالك، كاين خطر مرتفع ديال الفطريات والبياض.")
        elif fungal.get("level") == "MEDIUM":
            sentences.append("كاين شوية الخطر ديال الفطريات، حاول تراقب الشجر ديالك.")

        if weather.get("spray_blocked"):
            sentences.append("ماديرش الدوا اليوم علقاش كاين العجاج والريح دايز.")

        return " ".join(sentences)

    def explain(self, data: Dict[str, Any]) -> Dict[str, str]:
        return {
            "fr": self.generate_french(data),
            "darija": self.generate_darija(data)
        }

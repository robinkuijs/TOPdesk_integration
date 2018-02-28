# TOPdesk_integration
TOPdesk Incident Integration
In dit document wordt de koppeling beschreven die is gemaakt om meldingen vanuit de TOPdesk1 omgeving  
aan te maken in de TOPdesk2 omgeving. 
De koppeling is geschreven in Python en maakt gebruik van de TOPdesk API.

Het Python script wordt elke x minuut uitgevoerd. Hierbij wordt in TOPdesk1 gezocht naar meldingen die voldoen aan de volgende criteria:
- De melding is vandaag aangemaakt
- Het veld extern nummer is niet ingevuld
- De behandelaarsgroep is x
- De melding staat in de tweede lijn

Vervolgens wordt bepaald of het een incident of een RFI betreft op basis van de volgende criteria:

* Incident:
- Het veld "soort" melding is gelijk aan "Incident"
- Het veld "Escalatie vanuit" is gelijk aan "Standaard Platform Incident"

* RFI:
- Het veld "soort" melding is gelijk aan "RFI"
- Het veld "Escalatie vanuit" is gelijk aan "Standaard Platform RFI"

In het geval van een incident worden de volgende acties ondernomen:
- De inhoud van het incident wordt gekopieerd en met deze gegevens wordt een incident aangemaakt in TOPdesk2
	- De persoon wordt gekoppeld op basis van de achternaam en voornaam. Het is daarom belangrijk dat het veld achternaam en voornaam zowel in de bron als in de doeldatabase gelijk zijn
	- De impact en urgentie worden ingevuld bij het incident in TOPdesk2 en op basis hiervan wordt de prioriteit bepaald 	
- Het incidentnummer van het incident in TOPdesk2 wordt in TOPdesk1 ingevuld in het veld "extern nummer"
- De bestanden die als bijlage in het incident in TOPdesk1 staan worden gekopieerd naar het incident bij TOPdesk2

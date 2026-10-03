// Bilingual legal/information content for Upxero Ordering (EN primary, NL secondary).
// Long-form legal prose lives here as structured data selected by language; the small
// UI chrome (nav, footer labels, toggle) still uses the existing makeT() dictionary.
// Restaurant-owned content is never affected by this file.

export const COMPANY = {
  name: "Upxero OÜ",
  addressLines: ["Ahtri 12", "10151 Tallinn", "Estonia"],
  country: "Estonia (EU)",
  registry: "16534146",
  vat: "EE102522936",
  email: "info@upxero.com",
  website: "https://www.upxero.com",
  ordering: "https://order.upxero.com",
};

const UPDATED = "June 2026";

export const LEGAL = {
  privacy: {
    en: {
      title: "Privacy Policy",
      updated: `Last updated: ${UPDATED}`,
      sections: [
        {
          h: "1. Introduction",
          p: [
            "Upxero Ordering is a restaurant ordering software (SaaS) provided by Upxero OÜ (\"Upxero\", \"we\", \"us\"). This Privacy Policy describes the personal data that may be processed in connection with the Upxero Ordering application available at order.upxero.com, and the purposes for which it may be processed.",
            "This document is written as practical product and privacy information based on the current implementation of Upxero Ordering. It should be reviewed by Upxero before being treated as final legal documentation.",
          ],
        },
        {
          h: "2. Information we may process",
          p: ["Depending on how Upxero Ordering is used, the following categories of information may be processed."],
          sub: [
            { h: "Restaurant and account information", ul: ["name", "email address", "phone number (where applicable)", "login / account information", "restaurant name", "restaurant address / location", "staff account information", "account and security information"] },
            { h: "Customer ordering information", ul: ["customer name", "phone number", "email address", "delivery address (when delivery is selected)", "order contents", "order total", "order notes", "order status", "the order-status token used to access the secure order-status page"] },
            { h: "Restaurant and menu information", ul: ["restaurant name", "restaurant address / location", "menu categories", "menu items", "prices", "menu options", "menu item images", "uploaded menu PDF", "restaurant logo"] },
            { h: "Technical and security information", p: ["Where applicable, technical information may be processed for authentication, session and security purposes, abuse prevention, brute-force protection, maintaining the security of the service and diagnosing technical problems."] },
          ],
        },
        {
          h: "3. Purposes of processing",
          p: ["Data may be processed for purposes including:"],
          ul: ["providing Upxero Ordering", "creating and managing restaurant accounts", "managing staff accounts", "receiving and managing restaurant orders", "displaying order information to restaurants", "allowing customers to view order status", "sending transactional order and status emails", "managing menus and restaurant information", "providing delivery functionality", "maintaining security and preventing abuse", "operating and maintaining the service", "responding to support requests", "complying with applicable legal obligations"],
        },
        {
          h: "4. Restaurant and customer data responsibilities",
          p: [
            "A restaurant using Upxero Ordering may determine the purposes and means for which its customers' order information is processed. Depending on the specific processing activity, the restaurant and Upxero may have different responsibilities under applicable data-protection law.",
            "Upxero processes certain data in order to provide the Ordering service to restaurants. Upxero may separately process information for its own legitimate operational purposes, such as account management, security and support.",
          ],
        },
        {
          h: "5. Service providers",
          p: ["Upxero may use service providers that are necessary to operate the service, for example hosting infrastructure, database infrastructure, email delivery, file/storage infrastructure and other technical infrastructure providers required to operate Upxero Ordering. These providers process data on the basis required to deliver their part of the service."],
        },
        {
          h: "6. Order-status link",
          p: ["Customers do not need to create an account to place an order. After an order is placed, the customer can view its status through a secure order-status link that uses a token. In the current implementation this token expires 30 days after it is issued."],
        },
        {
          h: "7. Payment data",
          p: ["The current version of Upxero Ordering does not process or store customer payment-card information. Any future subscription billing relationship between Upxero and restaurants may use a third-party provider (such as Whop), but that is not part of the current ordering application."],
        },
        {
          h: "8. Your rights",
          p: ["Subject to applicable law and to the circumstances of the processing, you may have the following rights:"],
          ul: ["right of access", "right to rectification", "right to erasure (where applicable)", "right to restriction of processing (where applicable)", "right to object (where applicable)", "right to data portability (where applicable)", "right to withdraw consent (where processing is based on consent)", "right to lodge a complaint with a competent supervisory authority"],
        },
        {
          h: "9. Data retention",
          p: ["Personal data is retained only for as long as reasonably necessary for the relevant purposes, legal obligations, dispute resolution, security and legitimate business needs, subject to applicable law. Where a specific expiration period is implemented in the application, such as the 30-day order-status token, that period applies to the relevant data."],
        },
        {
          h: "10. Changes to this policy",
          p: ["We may update this Privacy Policy from time to time to reflect changes in the service or in applicable requirements. The latest version will be published on this page."],
        },
        {
          h: "11. Contact",
          p: ["For privacy questions you can contact us at info@upxero.com."],
        },
      ],
    },
    nl: {
      title: "Privacybeleid",
      updated: `Laatst bijgewerkt: juni 2026`,
      sections: [
        {
          h: "1. Inleiding",
          p: [
            "Upxero Ordering is bestelsoftware voor restaurants (SaaS) die wordt aangeboden door Upxero OÜ (\"Upxero\", \"wij\", \"ons\"). Dit Privacybeleid beschrijft welke persoonsgegevens kunnen worden verwerkt in verband met de Upxero Ordering-toepassing op order.upxero.com, en voor welke doeleinden.",
            "Dit document is opgesteld als praktische product- en privacy-informatie op basis van de huidige implementatie van Upxero Ordering. Het dient door Upxero te worden beoordeeld voordat het als definitieve juridische documentatie wordt beschouwd.",
          ],
        },
        {
          h: "2. Informatie die wij kunnen verwerken",
          p: ["Afhankelijk van hoe Upxero Ordering wordt gebruikt, kunnen de volgende categorieën informatie worden verwerkt."],
          sub: [
            { h: "Restaurant- en accountgegevens", ul: ["naam", "e-mailadres", "telefoonnummer (indien van toepassing)", "login- / accountgegevens", "restaurantnaam", "restaurantadres / locatie", "gegevens van medewerkersaccounts", "account- en beveiligingsgegevens"] },
            { h: "Bestelgegevens van klanten", ul: ["naam van de klant", "telefoonnummer", "e-mailadres", "bezorgadres (bij bezorging)", "inhoud van de bestelling", "besteltotaal", "opmerkingen bij de bestelling", "status van de bestelling", "het bestelstatus-token waarmee de beveiligde statuspagina kan worden geopend"] },
            { h: "Restaurant- en menugegevens", ul: ["restaurantnaam", "restaurantadres / locatie", "menucategorieën", "menu-items", "prijzen", "menu-opties", "afbeeldingen van menu-items", "geüploade menukaart (PDF)", "logo van het restaurant"] },
            { h: "Technische en beveiligingsgegevens", p: ["Waar van toepassing kan technische informatie worden verwerkt voor authenticatie, sessie- en beveiligingsdoeleinden, misbruikpreventie, bescherming tegen brute-force-aanvallen, het waarborgen van de beveiliging van de dienst en het oplossen van technische problemen."] },
          ],
        },
        {
          h: "3. Doeleinden van de verwerking",
          p: ["Gegevens kunnen worden verwerkt voor doeleinden zoals:"],
          ul: ["het aanbieden van Upxero Ordering", "het aanmaken en beheren van restaurantaccounts", "het beheren van medewerkersaccounts", "het ontvangen en beheren van bestellingen", "het tonen van bestelinformatie aan restaurants", "het laten bekijken van de bestelstatus door klanten", "het versturen van transactionele bestel- en status-e-mails", "het beheren van menu's en restaurantgegevens", "het bieden van bezorgfunctionaliteit", "het waarborgen van beveiliging en het voorkomen van misbruik", "het beheren en onderhouden van de dienst", "het beantwoorden van supportvragen", "het voldoen aan toepasselijke wettelijke verplichtingen"],
        },
        {
          h: "4. Verantwoordelijkheden voor restaurant- en klantgegevens",
          p: [
            "Een restaurant dat Upxero Ordering gebruikt kan de doeleinden en middelen bepalen waarvoor de bestelgegevens van zijn klanten worden verwerkt. Afhankelijk van de specifieke verwerkingsactiviteit kunnen het restaurant en Upxero verschillende verantwoordelijkheden hebben onder de toepasselijke wetgeving inzake gegevensbescherming.",
            "Upxero verwerkt bepaalde gegevens om de Ordering-dienst aan restaurants te leveren. Upxero kan daarnaast informatie verwerken voor eigen legitieme operationele doeleinden, zoals accountbeheer, beveiliging en support.",
          ],
        },
        {
          h: "5. Dienstverleners",
          p: ["Upxero kan gebruikmaken van dienstverleners die nodig zijn om de dienst te laten werken, bijvoorbeeld hostinginfrastructuur, database-infrastructuur, e-mailbezorging, bestands-/opslaginfrastructuur en andere technische infrastructuuraanbieders die nodig zijn om Upxero Ordering te laten werken. Deze aanbieders verwerken gegevens voor zover nodig om hun deel van de dienst te leveren."],
        },
        {
          h: "6. Bestelstatus-link",
          p: ["Klanten hoeven geen account aan te maken om te bestellen. Nadat een bestelling is geplaatst, kan de klant de status bekijken via een beveiligde statuslink met een token. In de huidige implementatie verloopt dit token 30 dagen nadat het is aangemaakt."],
        },
        {
          h: "7. Betaalgegevens",
          p: ["De huidige versie van Upxero Ordering verwerkt of bewaart geen betaalkaartgegevens van klanten. Een eventuele toekomstige abonnementsrelatie tussen Upxero en restaurants kan gebruikmaken van een externe aanbieder (zoals Whop), maar dat maakt geen deel uit van de huidige besteltoepassing."],
        },
        {
          h: "8. Uw rechten",
          p: ["Afhankelijk van de toepasselijke wetgeving en de omstandigheden van de verwerking kunt u de volgende rechten hebben:"],
          ul: ["recht op inzage", "recht op rectificatie", "recht op gegevenswissing (waar van toepassing)", "recht op beperking van de verwerking (waar van toepassing)", "recht van bezwaar (waar van toepassing)", "recht op overdraagbaarheid van gegevens (waar van toepassing)", "recht om toestemming in te trekken (waar de verwerking op toestemming is gebaseerd)", "recht om een klacht in te dienen bij een bevoegde toezichthoudende autoriteit"],
        },
        {
          h: "9. Bewaartermijn",
          p: ["Persoonsgegevens worden niet langer bewaard dan redelijkerwijs nodig is voor de betreffende doeleinden, wettelijke verplichtingen, geschillenbeslechting, beveiliging en legitieme bedrijfsbelangen, met inachtneming van de toepasselijke wetgeving. Waar een specifieke vervaltermijn in de toepassing is geïmplementeerd, zoals het bestelstatus-token van 30 dagen, geldt die termijn voor de betreffende gegevens."],
        },
        {
          h: "10. Wijzigingen in dit beleid",
          p: ["Wij kunnen dit Privacybeleid van tijd tot tijd bijwerken om wijzigingen in de dienst of in toepasselijke vereisten te verwerken. De meest recente versie wordt op deze pagina gepubliceerd."],
        },
        {
          h: "11. Contact",
          p: ["Voor privacyvragen kunt u contact met ons opnemen via info@upxero.com."],
        },
      ],
    },
  },

  terms: {
    en: {
      title: "Terms & Conditions",
      updated: `Last updated: ${UPDATED}`,
      sections: [
        { h: "1. The service", p: ["Upxero OÜ provides Upxero Ordering, restaurant ordering software (SaaS) that allows restaurants to receive and manage online orders for pickup and delivery. Upxero is the software provider."] },
        { h: "2. Restaurant responsibilities", p: ["The restaurant remains responsible for:"], ul: ["its food and products", "menu accuracy", "prices", "descriptions", "allergen and dietary information", "order acceptance and rejection", "food preparation", "pickup", "delivery", "customer refunds relating to its products and orders", "compliance with the laws applicable to its business"] },
        { h: "3. Account security", p: ["Each restaurant customer is responsible for:"], ul: ["keeping login credentials secure", "authorised staff access", "notifying Upxero of any unauthorised access", "appropriate use of staff accounts"] },
        { h: "4. Menu and content", p: ["Restaurant customers are responsible for the legality and accuracy of the content they upload or publish, including menu content, images, PDFs, restaurant information, prices and product descriptions."] },
        { h: "5. Orders", p: ["Upxero provides the technical ordering platform; the restaurant is responsible for fulfilling orders. Upxero does not guarantee that every order will be accepted or fulfilled."] },
        { h: "6. Availability", p: ["Reasonable efforts are made to operate the service, but it may occasionally be unavailable due to maintenance, updates, infrastructure problems, third-party service interruptions or circumstances outside Upxero's reasonable control."] },
        { h: "7. Subscriptions and payments", p: ["Upxero may offer paid subscriptions. Some customers may be invoiced directly by Upxero. Other customers may purchase subscriptions through a third-party platform such as Whop. Where a third-party platform processes payment, that provider's applicable payment terms may also apply. Third-party subscription checkout is not necessarily active in the current version of the application."] },
        { h: "8. Cancellation and termination", p: ["Customers may cancel according to their applicable subscription or invoice terms. Upxero may suspend or terminate access in appropriate circumstances, such as:"], ul: ["serious misuse", "security risks", "unlawful use", "non-payment", "material breach of these Terms"] },
        { h: "9. Intellectual property", p: ["Upxero retains all rights in its software, branding and platform. Restaurants retain ownership of their own content, subject to the licence necessary for Upxero to host, display and process that content as part of providing the service."] },
        { h: "10. Limitation of liability", p: ["To the maximum extent permitted by applicable law, Upxero provides the service \"as is\" and its liability in connection with the service is limited as set out in these Terms. Nothing in these Terms excludes or limits liability that cannot be excluded or limited under applicable law."] },
        { h: "11. Governing law", p: ["[The applicable governing law and jurisdiction should be confirmed by Upxero before these Terms are treated as final contractual terms.]"] },
        { h: "12. Changes to these Terms", p: ["Upxero may update these Terms from time to time. The latest version will be published on this page."] },
        { h: "13. Contact", p: ["For questions about these Terms you can contact us at info@upxero.com."] },
      ],
    },
    nl: {
      title: "Algemene voorwaarden",
      updated: `Laatst bijgewerkt: juni 2026`,
      sections: [
        { h: "1. De dienst", p: ["Upxero OÜ biedt Upxero Ordering aan, bestelsoftware voor restaurants (SaaS) waarmee restaurants online bestellingen voor afhalen en bezorgen kunnen ontvangen en beheren. Upxero is de softwareleverancier."] },
        { h: "2. Verantwoordelijkheden van het restaurant", p: ["Het restaurant blijft verantwoordelijk voor:"], ul: ["zijn voedsel en producten", "de juistheid van het menu", "prijzen", "omschrijvingen", "allergenen- en voedingsinformatie", "het accepteren en weigeren van bestellingen", "de voedselbereiding", "afhalen", "bezorgen", "terugbetalingen aan klanten met betrekking tot zijn producten en bestellingen", "naleving van de wetgeving die op zijn onderneming van toepassing is"] },
        { h: "3. Accountbeveiliging", p: ["Elke restaurantklant is verantwoordelijk voor:"], ul: ["het veilig bewaren van inloggegevens", "geautoriseerde toegang van medewerkers", "het melden van ongeoorloofde toegang aan Upxero", "passend gebruik van medewerkersaccounts"] },
        { h: "4. Menu en content", p: ["Restaurantklanten zijn verantwoordelijk voor de rechtmatigheid en juistheid van de content die zij uploaden of publiceren, waaronder menu-inhoud, afbeeldingen, PDF's, restaurantgegevens, prijzen en productomschrijvingen."] },
        { h: "5. Bestellingen", p: ["Upxero levert het technische bestelplatform; het restaurant is verantwoordelijk voor het afhandelen van bestellingen. Upxero garandeert niet dat elke bestelling wordt geaccepteerd of afgehandeld."] },
        { h: "6. Beschikbaarheid", p: ["Er worden redelijke inspanningen geleverd om de dienst te laten werken, maar deze kan af en toe niet beschikbaar zijn door onderhoud, updates, infrastructuurproblemen, onderbrekingen bij externe diensten of omstandigheden buiten de redelijke controle van Upxero."] },
        { h: "7. Abonnementen en betalingen", p: ["Upxero kan betaalde abonnementen aanbieden. Sommige klanten ontvangen mogelijk rechtstreeks een factuur van Upxero. Andere klanten kunnen een abonnement afsluiten via een extern platform zoals Whop. Wanneer een extern platform de betaling verwerkt, kunnen ook de toepasselijke betalingsvoorwaarden van die aanbieder gelden. Afrekenen via een extern abonnementsplatform is niet noodzakelijk actief in de huidige versie van de toepassing."] },
        { h: "8. Opzegging en beëindiging", p: ["Klanten kunnen opzeggen volgens hun toepasselijke abonnements- of factuurvoorwaarden. Upxero kan de toegang in passende omstandigheden opschorten of beëindigen, zoals bij:"], ul: ["ernstig misbruik", "beveiligingsrisico's", "onrechtmatig gebruik", "niet-betaling", "wezenlijke schending van deze voorwaarden"] },
        { h: "9. Intellectueel eigendom", p: ["Upxero behoudt alle rechten op zijn software, merk en platform. Restaurants behouden het eigendom van hun eigen content, onder de licentie die nodig is voor Upxero om die content te hosten, weer te geven en te verwerken als onderdeel van de dienstverlening."] },
        { h: "10. Beperking van aansprakelijkheid", p: ["Voor zover maximaal toegestaan onder de toepasselijke wetgeving wordt de dienst \"as is\" geleverd en is de aansprakelijkheid van Upxero in verband met de dienst beperkt zoals in deze voorwaarden uiteengezet. Niets in deze voorwaarden sluit aansprakelijkheid uit of beperkt deze waar dit volgens de toepasselijke wetgeving niet is toegestaan."] },
        { h: "11. Toepasselijk recht", p: ["[Het toepasselijke recht en de bevoegde rechter dienen door Upxero te worden bevestigd voordat deze voorwaarden als definitieve contractuele voorwaarden worden beschouwd.]"] },
        { h: "12. Wijzigingen in deze voorwaarden", p: ["Upxero kan deze voorwaarden van tijd tot tijd bijwerken. De meest recente versie wordt op deze pagina gepubliceerd."] },
        { h: "13. Contact", p: ["Voor vragen over deze voorwaarden kunt u contact met ons opnemen via info@upxero.com."] },
      ],
    },
  },

  cookies: {
    en: {
      title: "Cookie Policy",
      updated: `Last updated: ${UPDATED}`,
      sections: [
        { h: "1. Essential cookies and storage", p: ["Upxero Ordering uses only essential cookies and browser storage required for the application to function, for example:"], ul: ["authentication and session handling", "security", "essential application functionality (such as keeping a customer's cart on the ordering page)"] },
        { h: "2. No tracking or advertising", p: ["Upxero Ordering does not use Google Analytics, advertising trackers, marketing cookies or third-party tracking."] },
        { h: "3. Future changes", p: ["If Upxero introduces non-essential analytics, advertising or marketing cookies in the future, this cookie information and, where required, an appropriate consent mechanism may be updated accordingly."] },
        { h: "4. Contact", p: ["For questions about cookies you can contact us at info@upxero.com."] },
      ],
    },
    nl: {
      title: "Cookiebeleid",
      updated: `Laatst bijgewerkt: juni 2026`,
      sections: [
        { h: "1. Essentiële cookies en opslag", p: ["Upxero Ordering gebruikt uitsluitend essentiële cookies en browseropslag die nodig zijn om de toepassing te laten werken, bijvoorbeeld:"], ul: ["authenticatie en sessiebeheer", "beveiliging", "essentiële functionaliteit van de toepassing (zoals het bewaren van de winkelmand van een klant op de bestelpagina)"] },
        { h: "2. Geen tracking of advertenties", p: ["Upxero Ordering gebruikt geen Google Analytics, advertentietrackers, marketingcookies of tracking van derden."] },
        { h: "3. Toekomstige wijzigingen", p: ["Als Upxero in de toekomst niet-essentiële analyse-, advertentie- of marketingcookies introduceert, kan deze cookie-informatie en, waar vereist, een passend toestemmingsmechanisme dienovereenkomstig worden bijgewerkt."] },
        { h: "4. Contact", p: ["Voor vragen over cookies kunt u contact met ons opnemen via info@upxero.com."] },
      ],
    },
  },

  legal: {
    en: {
      title: "Legal & Company Information",
      sections: [
        { h: "Company", p: ["Upxero Ordering is operated by Upxero OÜ. Upxero is registered in Estonia through the Estonian e-Residency programme."] },
      ],
    },
    nl: {
      title: "Juridisch & bedrijfsinformatie",
      sections: [
        { h: "Bedrijf", p: ["Upxero Ordering wordt geëxploiteerd door Upxero OÜ. Upxero is in Estland geregistreerd via het Estse e-Residency-programma."] },
      ],
    },
  },

  contact: {
    en: {
      title: "Contact",
      sections: [
        { h: "Get in touch", p: ["For questions about Upxero Ordering, your account or these pages, please email us. We are happy to help."] },
      ],
    },
    nl: {
      title: "Contact",
      sections: [
        { h: "Neem contact op", p: ["Voor vragen over Upxero Ordering, uw account of deze pagina's kunt u ons een e-mail sturen. Wij helpen u graag verder."] },
      ],
    },
  },
};

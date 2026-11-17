/** English version of the Terms of Service (/termos?lang=en). Mirrors the Portuguese text. */
export function TermsEn() {
  return (
    <>
      <h2>1. Acceptance of the terms</h2>
      <p>
        By creating an account or using Auto Orbital ("we", "platform", "service"), you agree to these
        Terms of Service and to our <a href="/privacidade?lang=en">Privacy Policy</a>. If you do not agree
        with any part of them, do not use the service.
      </p>

      <h2>2. Description of the service</h2>
      <p>
        Auto Orbital is a web application (SaaS) operated by Raffa Studio Produções that lets users schedule
        and publish content to social media accounts they connect themselves. The service includes:
        (i) searching Shopee products and generating affiliate links; (ii) connecting social media accounts
        (Threads, Facebook, Instagram, TikTok and X, when available in the plan) through OAuth authorization;
        (iii) creating, scheduling and publishing content on those networks on the user's behalf, including
        text generated with artificial intelligence when the user chooses that feature; and (iv) showing
        metrics for posts published through the platform, when the network provides them.
      </p>
      <p>The service is open to the public. It is not an internal or personal-use tool.</p>

      <h2>3. Eligibility and registration</h2>
      <ul>
        <li>You must be at least 18 years old (or the age of legal majority in your country) to use the service.</li>
        <li>You must provide accurate information when registering and keep it up to date.</li>
        <li>You are responsible for keeping your password confidential and for all activity under your account.</li>
      </ul>

      <h2>3.1 Location and optional consent</h2>
      <p>
        To create an account you must acknowledge the Privacy Policy and accept the current Terms of Service.
        This acceptance is recorded with its version and date. It does not replace specific permissions for
        optional features.
      </p>
      <p>
        GPS location is optional and is not required for registration or for the core features. On first access
        the platform shows an explicit choice; only the allow button triggers a single browser query. If you
        allow it, approximate coordinates rounded on your device, the date and the estimated accuracy are saved
        to your account and may be shown individually to the administrator to plan commercial expansion.
        Refusing does not prevent registration, and after revocation the coordinates are deleted with no new
        collection. There is no continuous tracking. You can revoke and delete this data in Settings.
      </p>
      <p>See also <a href="/dados-coletados?lang=en">which device data may be processed</a>.</p>

      <h2>4. User responsibilities</h2>
      <p>By using Auto Orbital you agree to:</p>
      <ul>
        <li>Not use the service to send spam or misleading, illegal or infringing content;</li>
        <li>
          Comply with the terms and policies of each social network you connect (Threads, Facebook, Instagram,
          TikTok and X, when available in the plan). Connecting through OAuth does not exempt you from the
          network's own rules, including rules on branded or promotional content;
        </li>
        <li>
          Be fully responsible for the content you publish through the platform. Auto Orbital is a scheduling
          and publishing tool, not an editor or curator of user content;
        </li>
        <li>Follow each network's media and format limits (for example, MP4 video) and the platform's other quality requirements;</li>
        <li>Not try to access other users' accounts, data or credentials, or bypass the service's security mechanisms.</li>
      </ul>

      <h2>5. Third-party integrations</h2>
      <p>
        Auto Orbital depends on third-party APIs (Shopee, X, Meta/Facebook, Instagram, Threads, TikTok). We do not
        control their availability, policy changes, rate limits or outages, and we do not guarantee that publishing
        or data retrieval will work without interruption. If a social network revokes the OAuth authorization or
        suspends the user's account, the corresponding integration may stop working, and this is not a failure of
        our service.
      </p>

      <h2>6. Publishing and scheduling</h2>
      <p>
        Posts are sent only according to the user's configuration. We do not publish any content without the
        user's explicit authorization through the scheduling and publishing controls in the dashboard. Scheduling
        accepts a specific date and time or a recurrence of 1 to 7 days.
      </p>

      <h2>7. Paid plans</h2>
      <p>
        Paid plans, when offered, are charged through the payment provider Asaas, by credit card or Pix, at the
        price and billing cycle shown before payment. Card details are entered on Asaas's payment page and are not
        stored by Auto Orbital.
      </p>

      <h2>8. Limitation of liability</h2>
      <p>
        Auto Orbital is provided "as is". We do not guarantee sales, engagement or performance of posts published
        through the platform. To the fullest extent permitted by law, we are not liable for lost revenue, lost
        business opportunities or indirect damages arising from the use of the service, from the unavailability of
        integrated third-party APIs, or from actions taken by social networks on the user's account.
      </p>

      <h2>9. Intellectual property</h2>
      <p>
        The code, brand and interface of Auto Orbital belong to Raffa Studio Produções. Content you create and
        publish through the platform (text, images, videos, schedules) remains yours and under your responsibility.
      </p>

      <h2>10. Suspension and account closure</h2>
      <p>
        We may suspend or close an account that violates these terms or is used for fraudulent, abusive or illegal
        activity, or at the user's request. You can disconnect your social accounts at any time and request
        closure of your account and deletion of your data as described on the{' '}
        <a href="/exclusao-de-dados?lang=en">Data deletion</a> page.
      </p>

      <h2>11. Changes to these terms</h2>
      <p>
        We may update these Terms of Service to reflect changes in the service or in the applicable law. The date at
        the top of this page shows the current version. Continued use of the service after a published change means
        acceptance of the new terms.
      </p>

      <h2>12. Governing law and venue</h2>
      <p>
        These terms are governed by the laws of the Federative Republic of Brazil. The courts of the controller's
        domicile are chosen to settle disputes arising from these terms, without prejudice to the consumer's venue
        when required by law. If the Portuguese and English versions differ, the Portuguese version prevails.
      </p>

      <h2>13. Contact</h2>
      <p>
        Questions about these terms: <a href="mailto:contato.raffasp@gmail.com"><strong>contato.raffasp@gmail.com</strong></a>.
      </p>
    </>
  )
}

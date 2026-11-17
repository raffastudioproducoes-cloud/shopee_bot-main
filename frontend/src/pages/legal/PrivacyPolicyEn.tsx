/** English version of the Privacy Policy (/privacidade?lang=en). Mirrors the Portuguese text, which prevails. */
export function PrivacyPolicyEn() {
  return (
    <>
      <h2>1. Who we are</h2>
      <p>
        Auto Orbital is a web application that helps users publish content to their own social media accounts. The
        service is operated by <strong>Raffa Studio Produções</strong> (contact: contato.raffasp@gmail.com), which acts
        as the controller of the personal data processed on this platform under Brazil's General Data Protection Law
        (Law No. 13,709/2018, "LGPD") and, where applicable, the EU/UK General Data Protection Regulation ("GDPR").
      </p>

      <h2>2. Data we collect and how we use it</h2>
      <p>We collect and process the following data strictly to operate the service:</p>
      <ul>
        <li>
          <strong>Registration and identification data:</strong> full name, CPF (Brazilian taxpayer number), email and
          login credential. For email sign-up the password is managed by Supabase Auth; for Google sign-in, by Google.
          Legacy accounts may have a bcrypt password hash, never a plain-text password. The CPF is encrypted in the
          database and the interface never returns the full number.
        </li>
        <li>
          <strong>Additional account data:</strong> mobile phone (required to buy a plan); age, alternative email,
          phone, address and postal code are optional in the account profile. They are linked to the account,
          separately from social profiles.
        </li>
        <li>
          <strong>OAuth access tokens of the social networks</strong> the user connects (Threads, Facebook, Instagram,
          TikTok and X, when available in the plan): stored encrypted in the database (Fernet symmetric encryption) and
          never returned to the user's browser. The frontend only receives a status ("connected"/"disconnected").
        </li>
        <li>
          <strong>Shopee affiliate API credential</strong> (App ID and Secret pasted by the user): encrypted in the same
          way and validated against the Shopee API before being saved.
        </li>
        <li>
          <strong>The user's own AI keys</strong> (Google Gemini, OpenAI or Anthropic), used only when the user chooses
          to generate text with AI. Each key is stored encrypted.
        </li>
        <li><strong>Profiles, products and lists:</strong> profiles created, Shopee products searched and saved, and lists used in posts.</li>
        <li><strong>Post content:</strong> text, media and products linked to the posts the user creates and schedules.</li>
        <li>
          <strong>Media:</strong> uploaded images and videos are stored in Supabase Storage and accessed through
          temporary signed URLs (1 hour). Media drafts expire automatically after 24 hours.
        </li>
        <li>
          <strong>Data received from Shopee, Threads, Instagram, Facebook, TikTok and X:</strong> product, profile,
          media and post data within the permissions authorized when each network is connected (see section 2.3).
        </li>
        <li>
          <strong>Request logs (request_logs):</strong> route, HTTP method, status code, duration, source IP and, when
          signed in, the user. Collected only when audit logging is explicitly enabled on the server (off by default)
          and used only to debug failures.
        </li>
        <li>
          <strong>Audit events (audit_events):</strong> an immutable record of sensitive changes (who, when, before and
          after).
        </li>
      </ul>
      <p>
        <strong>Payments:</strong> paid plans are processed by Asaas (a Brazilian payment institution). To create the
        charge we send Asaas the account holder's name, CPF, email and mobile phone. Card details are entered on Asaas's
        payment page and never pass through or are stored by Auto Orbital; we only keep the Asaas customer ID, the plan,
        the amount, the payment method chosen (card or Pix) and the charge status. Filling in the registration does not
        create any charge.
      </p>

      <h2>2.1 Technical device data and optional GPS</h2>
      <p>
        When you access the site, the infrastructure may process your IP address, HTTP headers, technical browser
        information, paths accessed and response times for operation and security. See{' '}
        <a href="/dados-coletados?lang=en">What data does Auto Orbital use?</a>.
      </p>
      <p>
        GPS is <strong>entirely optional</strong>. Accepting the Terms does not authorize location. On first access a
        separate notice offers a one-time collection with browser permission. If allowed, latitude and longitude are
        rounded on the device (about 1 km) and sent once, with the date and estimated accuracy. The point is linked to
        the account and may be seen individually by the administrator for commercial planning. There is no background
        tracking, route history or use of location for advertising. You can refuse, correct and revoke it in Settings.
      </p>

      <h2>2.2 Post metrics and click counting</h2>
      <p>
        To show the performance of each post, we keep the history of the metrics each network provides for posts
        published through Auto Orbital (views, likes, comments, shares). We do not collect who liked, commented or
        viewed.
      </p>
      <p>
        In product posts, the Shopee link may be replaced by a short link on our own domain (<code>/r/…</code>) that
        redirects to the same affiliate link. It only records the <strong>aggregate number of clicks per link per
        day</strong>; we do not store the IP address, browser, device or any personal data of whoever clicked.
      </p>

      <h2>2.3 Data read from each connected social network</h2>
      <p>
        We only read data from accounts the user connects, and only to publish and show the performance of the user's
        own posts. We do not read private messages, follower lists or other people's data.
      </p>
      <table>
        <thead><tr><th>Network</th><th>Data read</th><th>Permissions</th></tr></thead>
        <tbody>
          <tr><td>Instagram (Meta)</td><td>Professional account ID and linked Facebook Page, username, media published by the app and metrics for those posts.</td><td><code>instagram_basic, instagram_content_publish, instagram_manage_insights, pages_show_list, pages_read_engagement</code></td></tr>
          <tr><td>Facebook (Meta)</td><td>User ID, Pages the user manages (ID, name, Page token), posts published by the app and metrics for those posts.</td><td><code>pages_show_list, pages_read_engagement, pages_manage_posts, read_insights</code></td></tr>
          <tr><td>Threads (Meta)</td><td>Profile ID, posts published by the app and metrics for those posts.</td><td><code>threads_basic, threads_content_publish, threads_manage_insights</code></td></tr>
          <tr><td>TikTok</td><td>Account ID (open_id) and display name, the account's posting options (creator_info) and the status of the uploaded video. We do not collect TikTok post metrics today.</td><td><code>user.info.basic, video.publish, video.upload</code></td></tr>
          <tr><td>X</td><td>Account ID and username and the IDs of posts and media sent by the app. We do not collect X post metrics today.</td><td><code>tweet.read, tweet.write, users.read, media.write, offline.access</code></td></tr>
        </tbody>
      </table>
      <p>
        Tokens for these accounts are encrypted in the database. Data received from Meta, TikTok and X platforms is used
        only for the purposes above, is not sold, is not used for advertising and is not shared with third parties other
        than the processors listed in section 4.
      </p>

      <h2>3. Legal bases</h2>
      <ul>
        <li><strong>Performance of a contract</strong> (LGPD art. 7, V; GDPR art. 6(1)(b)): account, login and the dashboard's core features.</li>
        <li><strong>Consent</strong> (LGPD art. 7, I; GDPR art. 6(1)(a)): connecting each social network and the Shopee credential. Nothing is connected without an explicit user action authorizing that specific scope (OAuth flow).</li>
        <li><strong>Specific, optional consent:</strong> location preferences and declared region, revocable independently of the Terms.</li>
        <li><strong>Legitimate interest</strong> (LGPD art. 7, IX; GDPR art. 6(1)(f)): request logs, when enabled, limited to security and technical diagnosis.</li>
      </ul>

      <h2>4. Who we share data with</h2>
      <p>We do not sell personal data. Data is shared only with:</p>
      <ul>
        <li><strong>The connected social networks</strong> (X, Facebook, Instagram, TikTok, Threads/Meta), within the permissions the user authorized, to publish content on the user's behalf.</li>
        <li><strong>Shopee</strong>, through its official affiliate API, to search products and generate affiliate links.</li>
        <li><strong>Infrastructure providers</strong> acting as processors on our instructions: database and storage at Supabase and the application hosted at Render. They do not use the data for their own purposes.</li>
        <li><strong>AI providers</strong> (Google Gemini, OpenAI and Anthropic), only when the user chooses to use their own key to generate text.</li>
        <li><strong>Asaas</strong>, to process payments for paid plans, with the data described in section 2.</li>
        <li><strong>Legacy media:</strong> temporary hosting at Cloudinary for older media until migration; Supabase Storage is the main media source.</li>
      </ul>
      <p>Some of these providers may process data outside Brazil (for example, in the United States), under their own safeguards for international transfers.</p>

      <h2>5. Data retention</h2>
      <ul>
        <li>Account and content data are kept while the account is active.</li>
        <li>When the user disconnects a social network or the Shopee credential in the dashboard, its token/App ID/Secret is erased immediately; the empty credential record is kept for auditing.</li>
        <li>When Meta notifies us that a user removed the app or requested deletion, the credentials linked to that account are erased (see section 9).</li>
        <li>Media drafts expire after 24 hours; signed media links expire after 1 hour.</li>
        <li>Request logs are deleted automatically after <strong>90 days</strong>.</li>
        <li>Post metric history is kept while the account exists.</li>
        <li>After an account deletion request, account data is deleted, except records we must keep by law (for example, payment and tax records) or immutable audit events.</li>
      </ul>

      <h2>6. Security</h2>
      <ul>
        <li>OAuth tokens and third-party credentials are encrypted at rest (Fernet).</li>
        <li>Passwords are stored only as hashes, never in plain text.</li>
        <li>All communication with the dashboard uses HTTPS.</li>
        <li>The session is kept in an <strong>httpOnly</strong>, <strong>Secure</strong>, <strong>SameSite=Lax</strong> cookie, not readable by JavaScript.</li>
        <li>New passwords are checked against public breaches with Have I Been Pwned using <em>k-anonymity</em>: only the first 5 characters of a SHA-1 hash are sent.</li>
        <li>The database uses Row Level Security (RLS), blocking direct access outside the official API.</li>
      </ul>

      <h2>7. Your rights</h2>
      <p>Under the LGPD (arts. 9 and 18) and, where applicable, the GDPR, you may at any time request:</p>
      <ul>
        <li>Confirmation that we process your data and access to it;</li>
        <li>Correction of incomplete, inaccurate or outdated data;</li>
        <li>Deletion of your data;</li>
        <li>Withdrawal of consent for any connected social network (disconnect it in the dashboard or ask by email);</li>
        <li>Portability of your data (the dashboard exports a JSON backup);</li>
        <li>Information about who your data is shared with;</li>
        <li>Restriction of or objection to processing, and lodging a complaint with your data protection authority (ANPD in Brazil, or your local authority in the EEA/UK).</li>
      </ul>
      <p>Send requests to the contact in section 11. We reply within 15 days.</p>

      <h2>8. Cookies</h2>
      <p>
        Auto Orbital only uses the essential authentication cookie <strong>access_token</strong> (JWT), which keeps you
        signed in. It is httpOnly, Secure and SameSite=Lax. We do not use tracking, analytics or marketing cookies or
        pixels. The site may remember interface preferences (such as the chosen language) in your browser.
      </p>

      <h2>9. How to delete or disconnect your data</h2>
      <p>Full step-by-step instructions are on the public <a href="/exclusao-de-dados?lang=en">Data deletion</a> page. In short:</p>
      <ol>
        <li><strong>Disconnect social networks</strong> on the Credentials page ("Disconnect" on each network). The token is erased from our server immediately.</li>
        <li><strong>Remove the app in the network itself</strong> (Facebook/Instagram/Threads app settings, TikTok "Manage app permissions", X "Connected apps").</li>
        <li><strong>Export a backup</strong> in Settings if you want a copy of your data.</li>
        <li><strong>Delete your account</strong> in Settings → "Backup e dados" → "Excluir minha conta e dados" (requires your password; if the dashboard says self-service deletion is not available yet, use email), or email <strong>contato.raffasp@gmail.com</strong> from your account email asking for deletion.</li>
        <li>
          <strong>Automatic Meta notice (Facebook/Instagram/Threads):</strong> when you remove the app from Facebook,
          Instagram or Threads, Meta notifies Auto Orbital automatically (endpoints <code>/api/meta/deauthorize</code>,{' '}
          <code>/api/meta/data-deletion</code>, <code>/api/threads/uninstall</code> and <code>/api/threads/delete</code>)
          and the credentials and data linked to that account are erased. Meta receives a confirmation code and a status
          link where you can follow the request.
        </li>
      </ol>

      <h2>10. Children</h2>
      <p>Auto Orbital is not intended for minors. You must be at least 18 years old (or the age of majority in your jurisdiction). If we find that an account belongs to a minor, we may delete its data.</p>

      <h2>11. Contact and data protection officer</h2>
      <p>Questions about this policy or requests about your personal data: <a href="mailto:contato.raffasp@gmail.com"><strong>contato.raffasp@gmail.com</strong></a>.</p>

      <h2>12. Changes to this policy</h2>
      <p>
        This policy may be updated to reflect changes in the service or the law. The date at the top shows the current
        version. Relevant changes will be announced by email or in the dashboard. If the Portuguese and English versions
        differ, the Portuguese version prevails.
      </p>
    </>
  )
}

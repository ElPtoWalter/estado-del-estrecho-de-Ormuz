"""Synthetic fixtures only; no real identity, forwarding address or account result."""
import copy,csv,json,tempfile,unittest
from pathlib import Path
import indexation_audit as audit
import publisher_preparation as prep
import build_public_site as public

class EvidenceTests(unittest.TestCase):
    def test_source_and_built_sitemap_layers_are_independent(self):
        def xml(paths):return ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+audit.BASE+p+'</loc></url>' for p in paths)+'</urlset>').encode()
        a=audit.layer(xml(['source.html','diario/2026-08-10.html']),'source','sitemap.xml');b=audit.layer(xml(['public.html']),'built','_site/sitemap.xml')
        self.assertEqual(a['url_count'],2);self.assertEqual(b['url_count'],1);self.assertNotEqual(a['sha256_lf'],b['sha256_lf'])
    def test_previous_utc_date_can_be_same_madrid_edition(self):
        self.assertEqual(audit.local_date('2026-08-09T22:52:15Z'),'2026-08-10');self.assertIsNone(audit.local_date('2026-08-09T22:52:15'))
        h='<script type="application/ld+json">{"datePublished":"2026-08-09T22:52:15Z"}</script><main><time datetime="2026-08-10">Edition</time><p>Public text.</p></main>'
        self.assertEqual(audit.diary_facts('diario/2026-08-10.html',h)['temporal_review_flags'],[])
        self.assertIn('fecha_schema_local_distinta_de_edicion',audit.diary_facts('diario/2026-08-10.html',h.replace('2026-08-09T22:52:15Z','2026-08-11T10:00:00Z'))['temporal_review_flags'])
    def test_repetition_does_not_mutate_editorial_policy(self):
        h='<meta name="robots" content="index,follow"><main><time datetime="2026-08-10"></time><p>Repeated paragraph.</p><p>Repeated paragraph.</p></main>'
        f=audit.diary_facts('diario/2026-08-10.html',h)
        self.assertEqual(f['robots'],'index,follow');self.assertEqual(len(f['repeated_paragraphs']),1)
    def test_account_template_is_blank_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);r={'research':[{'url':audit.BASE+'original.html'}],'diary_in_source_sitemap':[]};audit.write_report(r,out)
            with (out/'url-inspection-template.csv').open(encoding='utf-8') as stream:row=next(csv.DictReader(stream))
            self.assertEqual(row['account_status'],'pendiente_cuenta_externa')
            for field in audit.ACCOUNT_FIELDS:self.assertEqual(row[field],'')
            (out/'url-inspection-template.csv').write_text('Existing private work copy',encoding='utf-8')
            audit.write_report(r,out);self.assertEqual((out/'url-inspection-template.csv').read_text(),'Existing private work copy')
    def test_actual_snapshot_does_not_infer_google_indexing(self):
        r=json.loads((prep.ROOT/'docs/preflight-20261028/sitemap-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(r['source_sitemap']['kind'],'repository_source');self.assertEqual(r['generated_sitemap']['kind'],'generated_public_artifact');self.assertEqual(r['deployed_sitemap']['kind'],'http_deployed')
        self.assertEqual(len(r['research']),6);self.assertIsNone(r['search_console_indexed_count']);self.assertFalse(r['editorial_decisions_changed'])
        for row in r['research']:self.assertEqual(row['public_http_status'],200);self.assertFalse(row['google_indexing_confirmed'])

class PreparationTests(unittest.TestCase):
    def test_receipt_is_a_statement_not_a_sending_or_account_test(self):
        v=prep.state();self.assertEqual(v['incoming_mail']['status'],'confirmed_by_owner_statement');self.assertFalse(v['incoming_mail']['independently_tested'])
        self.assertEqual(v['outgoing_domain_identity']['status'],'not_verified')
        for k in ('legal_compliance_confirmed','legal_identity_complete','adsense_account_verified','cmp_verified','ready_for_resubmission'):self.assertIs(v[k],False)
        self.assertTrue(all(x is False for x in v['permissions'].values()))
    def test_private_fields_and_expanded_authorizations_are_rejected(self):
        v=prep.state();variants=[]
        x=copy.deepcopy(v);x['forwarding_destination']='FIELD_NOT_PERMITTED';variants.append(x)
        x=copy.deepcopy(v);x['permissions']['send_email']=True;variants.append(x)
        x=copy.deepcopy(v);x['outgoing_domain_identity']['status']='verified';variants.append(x)
        x=copy.deepcopy(v);x['legal_identity_complete']=True;variants.append(x)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for variant in variants:
                (root/'publisher-preparation.json').write_text(json.dumps(variant),encoding='utf-8')
                with self.assertRaises(ValueError):prep.state(root)
    def test_refresh_retains_history_without_inventing_another_review(self):
        r=prep.enrich(json.loads((prep.ROOT/'adsense-readiness-report.json').read_text(encoding='utf-8')))
        self.assertFalse(r['ready_for_resubmission']);self.assertEqual(r['account_approval'],'not_verified');self.assertIn('historical_snapshot_20261024',r)
        self.assertFalse(r['publication_evidence']['new_human_review_recorded']);self.assertFalse(r['publication_evidence']['external_legal_clearance_asserted'])
        self.assertNotIn('contact_receipt_and_reply',r['owner_confirmation']);self.assertTrue(r['publication_evidence']['pr25_deployed_verified_by_http'])
    def test_missing_declaration_never_creates_receipt_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=prep.enrich({'ready_for_resubmission':True},Path(tmp));self.assertFalse(r['ready_for_resubmission']);self.assertNotIn('owner_confirmation',r)
    def test_public_proposals_preserve_limits_and_no_advertising(self):
        for name in ('aviso-legal.html','privacidad.html','contacto.html','en-legal.html','en-privacy.html','en-contact.html'):
            t=(prep.ROOT/name).read_text(encoding='utf-8');self.assertIn('declaración del titular' if not name.startswith('en-') else 'owner’s statement',t)
            self.assertRegex(t,r'sin comprobarse|No se ha comprobado' if not name.startswith('en-') else r'unverified')
        t=public.sanitize_html((prep.ROOT/'aviso-legal.html').read_text(encoding='utf-8'),'aviso-legal.html')
        self.assertIn('declaración del titular',t);self.assertNotIn('adsbygoogle.js',t)
    def test_resubmission_and_all_four_monetization_gates_remain_false(self):
        prep.check();v=json.loads((prep.ROOT/'monetization.json').read_text(encoding='utf-8'))['adsense']
        for k in ('enabled','account_ready','cmp_verified','publisher_identity_complete'):self.assertIs(v[k],False)

if __name__=='__main__':unittest.main()

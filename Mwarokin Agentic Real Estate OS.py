import React, { useEffect, useState } from 'react';
import Head from 'next/head';
import { useRouter } from 'next/router';
import { ThemeProvider } from './ThemeContext';
import Header from '../components/Header';
import Footer from '../components/Footer';
import ListingCard from '../components/ListingCard';
import SearchBar from '../components/SearchBar';

// Tenant configuration type
interface TenantConfig {
  tenant_id: string;
  name: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  typography: string;
  domain: string;
  locale: string;
  currency: string;
}

// Listing type (aligned with backend)
interface Listing {
  listing_id: string;
  address: string;
  city: string;
  asking_price: number;
  bedrooms: number;
  amenities: string[];
  images: string[];
}

// Match type (aligned with backend)
interface Match {
  listing_id: string;
  score: number;
  explanation: string;
}

const Home: React.FC = () => {
  const router = useRouter();
  const { tenant_id } = router.query;
  const [tenantConfig, setTenantConfig] = useState<TenantConfig | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [searchProfile, setSearchProfile] = useState({
    city: '',
    intent: 'buy',
    min_bedrooms: 0,
    max_price: 0,
    must_have: [] as string[],
  });

  // Fetch tenant configuration
  useEffect(() => {
    if (tenant_id) {
      fetch(`/api/tenant/${tenant_id}`)
        .then((res) => res.json())
        .then((data) => setTenantConfig(data))
        .catch((err) => console.error('Error fetching tenant config:', err));
    }
  }, [tenant_id]);

  // Fetch listings for tenant
  useEffect(() => {
    if (tenant_id) {
      fetch(`/api/listings?tenant_id=${tenant_id}`)
        .then((res) => res.json())
        .then((data) => setListings(data))
        .catch((err) => console.error('Error fetching listings:', err));
    }
  }, [tenant_id]);

  // Handle search submission
  const handleSearch = async () => {
    try {
      const res = await fetch(`/api/matchmaking?tenant_id=${tenant_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchProfile),
      });
      const matches = await res.json();
      setMatches(matches);
    } catch (err) {
      console.error('Error fetching matches:', err);
    }
  };

  if (!tenantConfig) {
    return <div>Loading...</div>;
  }

  return (
    <ThemeProvider
      theme={{
        primaryColor: tenantConfig.primary_color,
        secondaryColor: tenantConfig.secondary_color,
        typography: tenantConfig.typography,
      }}
    >
      <Head>
        <title>{tenantConfig.name} - Real Estate</title>
        <meta name="description" content={`Find properties with ${tenantConfig.name}`} />
        <meta name="keywords" content="real estate, properties, buy, rent" />
        <link rel="icon" href={tenantConfig.logo_url} />
      </Head>
      <div className="min-h-screen flex flex-col">
        <Header logo={tenantConfig.logo_url} name={tenantConfig.name} />
        <main className="flex-grow container mx-auto p-4">
          <SearchBar
            profile={searchProfile}
            onChange={setSearchProfile}
            onSearch={handleSearch}
            currency={tenantConfig.currency}
          />
          {matches.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {matches.map((match) => (
                <ListingCard
                  key={match.listing_id}
                  listing={listings.find((l) => l.listing_id === match.listing_id)}
                  score={match.score}
                  explanation={match.explanation}
                />
              ))}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {listings.map((listing) => (
                <ListingCard key={listing.listing_id} listing={listing} />
              ))}
            </div>
          )}
        </main>
        <Footer name={tenantConfig.name} />
      </div>
    </ThemeProvider>
  );
};

export default Home;
import asyncio

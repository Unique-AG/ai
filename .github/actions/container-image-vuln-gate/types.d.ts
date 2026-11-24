export interface TrivyPkgIdentifier {
	PURL?: string;
	UID?: string;
}

export interface TrivyVulnerability {
	VulnerabilityID?: string;
	PkgID?: string;
	PkgName?: string;
	PkgIdentifier?: TrivyPkgIdentifier;
	InstalledVersion?: string;
	FixedVersion?: string | null;
	Severity?: string;
	PrimaryURL?: string;
	Layer?: {
		DiffID?: string;
		Digest?: string;
	};
}

export interface TrivyPackage {
	ID?: string;
	Name?: string;
	Version?: string;
}

export interface TrivyResult {
	Target?: string;
	Class?: string;
	Type?: string;
	Packages?: TrivyPackage[];
	Vulnerabilities?: TrivyVulnerability[];
}

export interface TrivyScan {
	Metadata?: {
		DiffIDs?: string[];
	};
	Results?: TrivyResult[];
}

export interface ClassifiedFinding extends TrivyVulnerability {
	origin: "inherited" | "introduced";
	resultClass?: string;
	resultType?: string;
	resultTarget?: string;
}

export interface ClassificationResult {
	inherited: ClassifiedFinding[];
	introduced: ClassifiedFinding[];
	inheritedFixable: ClassifiedFinding[];
	inheritedUnfixable: ClassifiedFinding[];
	introducedFixable: ClassifiedFinding[];
	introducedUnfixable: ClassifiedFinding[];
}

export interface SeverityPartition {
	blocking: ClassifiedFinding[];
	advisory: ClassifiedFinding[];
}

export interface ScanCoverage {
	layers: number;
	osPackages: number;
	languagePackages: number;
	targets: string[];
}

export interface LayerVerification {
	ok: boolean;
	reason?: string;
	baseDiffIds?: string[];
}
